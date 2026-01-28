from typing import List
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from AgentPrompts import supervisor_behavior, behavior_prompt, evaluator_behavior, supervisor_prompt, evaluator_prompt
from AgentState import AgentState
from AgentTools import tools
from ConfigurationManager import ConfigurationManager
from Helpers import print_debug


class LocalAgent:
    def __init__(self):
        # initialize the base model to be used
        agent_config = ConfigurationManager.get_configuration("agent")
        supervisor_config = ConfigurationManager.get_configuration("supervisor")
        self.force_reflection_issues = supervisor_config["forceReflectionIssues"]

        self.base_model = init_chat_model(
            model=agent_config["model"],
            base_url=agent_config["baseUrl"],
            model_provider="openai",
            temperature=0.8,
            api_key="none",
            stop=["<|im_start|>", "<|im_end|>"])
        self.eval_model = init_chat_model(
            model=supervisor_config["model"],
            base_url=supervisor_config["baseUrl"],
            model_provider="openai",
            api_key="none",
            temperature=0.1,
            stop=["<|im_start|>", "<|im_end|>"])

        # allow agent usage of the implemented tools
        self.tools_model = self.base_model.bind_tools(tools)

        pipeline = StateGraph(AgentState)
        pipeline.add_node("reason", self.reason)
        pipeline.add_node("tools", ToolNode(tools))
        pipeline.add_node("reflect", self.reflect)
        pipeline.add_node("evaluate", self.evaluate)
        pipeline.set_entry_point("reason")

        pipeline.add_conditional_edges("reason", self.edge_from_reason)
        pipeline.add_conditional_edges("reflect", self.edge_from_reflection)
        pipeline.add_conditional_edges("evaluate", self.edge_from_evaluate)

        pipeline.add_edge("tools", "reason")

        self.agent = pipeline.compile()

    async def reason(self, state: AgentState, config: RunnableConfig):
        full_response = None

        async for chunk in self.tools_model.astream(state["messages"], config=config):
            if full_response is None:
                full_response = chunk
            else:
                full_response += chunk

        full_response.name = "Captain the Helpful"

        return {
            "messages": [full_response],
            "iterations": state["iterations"] + 1
        }

    async def reflect(self, state: AgentState, config: RunnableConfig):
        has_tool_calls = False
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage) and not msg.name:
                break
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                has_tool_calls = True
                break

        prompt = list(state["messages"])
        prompt[0] = SystemMessage(content=supervisor_behavior(self.force_reflection_issues, has_tool_calls))
        prompt.append(HumanMessage(content=supervisor_prompt()))

        full_reflection = None
        async for chunk in self.eval_model.astream(prompt, config=config):
            if full_reflection is None:
                full_reflection = chunk
            else:
                full_reflection += chunk

        self.force_reflection_issues = False
        return {
            "messages": [HumanMessage(content=full_reflection.content.split("</think>")[-1], name="First Mate the Watchful")],
            "iterations": state["iterations"]
        }

    async def evaluate(self, state: AgentState, config: RunnableConfig):
        messages = list(state["messages"])[:-1]

        prompt = self.get_last_human_message(messages)
        prompt.insert(0, SystemMessage(content=evaluator_behavior()))
        prompt.append(HumanMessage(content=evaluator_prompt()))

        full_eval = None
        async for chunk in self.eval_model.astream(prompt, config=config):
            if full_eval is None:
                full_eval = chunk
            else:
                full_eval += chunk

        return {
            "messages": [HumanMessage(content=full_eval.content, name="Quartermaster the JudgeMaster")],
            "iterations": state["iterations"]
        }

    @staticmethod
    def edge_from_reason(state: AgentState):
        last_msg = state["messages"][-1]

        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            print_debug(" -> tools")
            return "tools"
        print_debug(" -> reflect")
        return "reflect"

    @staticmethod
    def edge_from_evaluate(state: AgentState):
        print_debug(" -> END")
        return END

    @staticmethod
    def edge_from_reflection(state: AgentState):
        if state["iterations"] > 5:
            print_debug(" -> evaluate (max iterations reached)")
            return "evaluate"

        if len(state["messages"]) > 0 and "APPROVED" in state["messages"][-1].content.split("</think>")[-1].strip():
            print_debug(" -> evaluate (APPROVED)")
            return "evaluate"

        print_debug(" -> reason")
        return "reason"

    async def gui_chat_async(self, messages: List[BaseMessage]):
        start_state = {"messages": messages, "iterations": 0}
        start_state["messages"].insert(0, SystemMessage(content=behavior_prompt()))

        last_reason_content = ""
        buffer = ""
        tags_to_replace = {
            "<think>": "_Thinking..._",
            "</think>": "_Output:_"
        }
        states = {
            "reason": "🧠 **Reasoning**",
            "reflect": "🔍 **Reflecting**",
            "evaluate": "⚖️ **Evaluating**",
            "tools": "🛠️ **Tool call**"
        }
        longest_tag_length = max(len(t) for t in tags_to_replace.keys()) + 1

        try:
            # all intermediate messages will be part of a thinking block to keep the chat clean
            yield "<think>\n\n"

            print_debug("reflect")
            # start streaming the events from the graph
            async for event in self.agent.astream_events(start_state, version="v2"):
                kind = event["event"]
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")

                # track which node are we about to enter
                # need to check with the metadata as well,
                # because "on_chain_start" is triggered multiple times per state change
                if kind == "on_chain_start" and node_name and event["name"] == node_name:
                    # we only want to store the final reasoning output, so we clear the variable on entering the node
                    if node_name == "reason":
                        last_reason_content = ""
                    if len(buffer) > 0:
                        raise ValueError

                    state_name = states.get(node_name, f"**Node: {node_name}**")
                    yield f"\n\n{state_name}\n---\n\n"

                elif kind == "on_tool_start":
                    yield f"\n🛠️ **Executing Tool:** `{event['name']}` with input: `{event['data'].get('input')}`\n"

                elif kind == "on_tool_end":
                    tool_output = event["data"].get("output")
                    content = tool_output.content if hasattr(tool_output, 'content') else str(tool_output)
                    yield f"\n✅ **Tool Result:**\n```json\n{content}\n```\n"

                # process the token output of the nodes
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if not content:
                        continue

                    # store reason content for the final yield
                    if node_name == "reason":
                        last_reason_content += content

                    buffer += content

                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        buffer += "\n" + chunk.usage_metadata

                    output, buffer = self._consume_buffer(buffer, tags_to_replace, longest_tag_length)
                    if output:
                        yield output

                # add separator between nodes
                elif kind == "on_chain_end" and node_name and event["name"] == node_name: # and "langgraph_node" in event["metadata"]:
                    output, buffer = self._consume_buffer(buffer, tags_to_replace, longest_tag_length, force_flush=True)
                    if output:
                        yield output
                    if len(buffer) > 0:
                        raise ValueError("Buffer should be empty after flushing.")
                    yield "\n\n---\n\n"

            final_answer = last_reason_content.split("</think>")[-1].strip()
            yield f"</think>\n\n{final_answer}"

        except Exception as e:
            print(f"Error in graph: {e}")
            yield f"</think>\n\n**Error:** {str(e)}"

    @staticmethod
    def _consume_buffer(buffer: str, tags: dict, longest_tag: int, force_flush: bool = False):
        out = []

        # process the buffer
        while buffer:
            # look for a matching tag in the buffer
            tag_found = False
            for tag, replacement in tags.items():
                if tag in buffer:
                    before, after = buffer.split(tag, 1)
                    # output the content before the tag + the replacement for the tag
                    out.append(before + replacement)
                    # save the remaining data for later processing
                    buffer = after
                    tag_found = True
                    break

            # try again looking for another tag, just in case
            if tag_found:
                continue

            # we force output when we are about to transition between nodes, so there will be no more tokens
            # coming from the current node anyway, therefore there will be no new tag created
            if force_flush:
                out.append(buffer)
                buffer = ""
                return "".join(out), buffer

            # whole tag not found, check if its possible we have part of the tag in buffer
            if "<" in buffer:
                idx = buffer.find("<")
                # we found a possible start of the tag
                if idx > 0:
                    # text BEFORE the "<" is safe to yield
                    out.append(buffer[:idx])
                    # recheck the buffer starting with "<"
                    buffer = buffer[idx:]
                    continue

                # buffer now starts with "<", so we check whether the buffer is longer that our longest tag
                if len(buffer) >= longest_tag:
                    # it is longer, so this "<" is not start of the tags we care about
                    # e.g. it could be a part of a math equation
                    # yield the angle bracket and leave rest of the buffer for the next processing
                    # we cannot yield the whole buffer since it may contain another "<" which we need to check
                    out.append(buffer[0])
                    buffer = buffer[1:]
                else:
                    # buffer is shorter than a tag, so it might be part of some tag we want to replace
                    # stop processing and wait for more tokens.
                    break
            else:
                # No "<" in the buffer, send it over
                out.append(buffer)
                buffer = ""

        return "".join(out), buffer

    @staticmethod
    def get_last_human_message(messages: List[BaseMessage]):
        human_index = next((i for i in reversed(range(len(messages))) if messages[i].type == "human"
                                                                    and (not messages[i].name or len(messages[i].name) == 0)),
                           ValueError("No human message found"))
        return messages[human_index:]
