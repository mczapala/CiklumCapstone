import asyncio

import langchain.messages
from langchain_openai import ChatOpenAI
from statistics import mean

from ragas import evaluate, EvaluationDataset, SingleTurnSample, RunConfig
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from ragas.llms import LangchainLLMWrapper
from ConfigurationManager import ConfigurationManager

questions = [
    "Who assigns students to their house?",
    "Which schools participated in the Triwizard tournament?",
    "How do students travel to Hogwarts?",
    "Who was the prisoner of Azkaban?"
]
ground_truths = [
    "Sorting hat",
    "Hogwarts, Beauxbatons Academy and Durmstrang Institute",
    "Hogwarts express",
    "Sirius Black"
]

class RagasEvaluator:
    def __init__(self, rag_chain):
        cfg = ConfigurationManager.get_configuration("ragas")
        self.rag_chain = rag_chain

        raw_client = ChatOpenAI(
            base_url=cfg["baseUrl"],
            api_key="lm-studio",
            model=cfg["model"],
            timeout=1200
        )

        self.ragas_llm = LangchainLLMWrapper(raw_client)

        self.metrics = [
            Faithfulness(llm=self.ragas_llm),
            ContextPrecision(llm=self.ragas_llm),
            ContextRecall(llm=self.ragas_llm)
        ]

        self.run_config = RunConfig(timeout=1200, max_workers=1)

    def run_eval(self):
        print(f"Running inference on {len(questions)} questions")

        samples = []
        for i, question in enumerate(questions):
            # Run inference
            result = asyncio.run(self.rag_chain.invoke([langchain.messages.HumanMessage(content=question)]))["messages"]

            # Extract Answer
            answer = result[next((i for i in reversed(range(len(result))) if result[i].type == "ai"),
                           ValueError("No AI message found"))].content.split("</think>")[-1]

            tools_content = [item.content for item in result if item.type == "tool"]

            # Create Sample
            sample = SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=tools_content,
                reference=ground_truths[i] if ground_truths else None
            )
            samples.append(sample)

        # Run Evaluation
        dataset = EvaluationDataset(samples=samples)
        print("\nStarting Ragas Evaluation")

        results = evaluate(
            dataset=dataset,
            metrics=self.metrics,
            run_config=self.run_config,
        )

        question_no = 0
        for x in results.scores:
            print(f"{question_no+1}. {questions[question_no]}")
            print(f"\tFaithfulness: {x['faithfulness']}")
            print(f"\tContext recall: {x['context_recall']}")
            print(f"\tContext precision: {x['context_precision']}")
            question_no += 1

        print("\nEvaluation score:")
        print(f"\tFaithfulness: {mean([x['faithfulness'] for x in results.scores])}")
        print(f"\tContext recall: {mean([x['context_recall'] for x in results.scores])}")
        print(f"\tContext precision: {mean([x['context_precision'] for x in results.scores])}")
