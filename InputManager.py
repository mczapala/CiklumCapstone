from LocalAgent import LocalAgent
from KnowledgeManager import KnowledgeManager
from RagasEvaluator import RagasEvaluator

def print_commands():
    print("Available commands are:"
      "\n\t/import_pdf <path> - imports the pdf file to knowledge base"
      "\n\t/import_audio <path> - imports the audio file to knowledge base"
      "\n\t/evaluate - run ragas evaluation"
      "\n\t/exit (or /quit) - exits the application (or, when in chat mode, exists chat mode)"
      "\n\t/help - displays this message")


class InputManager:
    def __init__(self):
        self.agent = LocalAgent()
        self.knowledgeManager = KnowledgeManager()
        self.evaluator = RagasEvaluator(rag_chain=self.agent)

    def start(self):
        print("Welcome to the Capstone project!")
        print_commands()
        while True:
            user_input = input("$ ")
            if user_input.startswith("/import_audio "):
                self.knowledgeManager.import_audio(user_input[13:].strip())
            elif user_input.startswith("/import_pdf "):
                self.knowledgeManager.import_pdf(user_input[11:].strip())
            elif user_input.startswith("/exit") or user_input.startswith("/quit"):
                break
            elif user_input.startswith("/help"):
                print_commands()
            elif user_input.startswith("/eval"):
                self.evaluator.run_eval()
            else:
                print("Invalid input. ")
                print_commands()
