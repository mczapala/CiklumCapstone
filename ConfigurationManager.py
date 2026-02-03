import os
import pathlib

import yaml

root_dir = pathlib.Path(__file__).parent
class ConfigurationManager:
    @staticmethod
    def get_configuration(key: str):
        with open(os.path.join(root_dir, "config.yaml"), 'r') as stream:
            config = yaml.safe_load(stream)

        if key not in config:
            raise Exception(f'{key} not defined in configuration')

        return config[key]