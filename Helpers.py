from ConfigurationManager import ConfigurationManager

debugOutput = ConfigurationManager.get_configuration("debugOutput")

def print_debug(text: str, end: str = ""):
    if debugOutput:
        print(text, end=end)