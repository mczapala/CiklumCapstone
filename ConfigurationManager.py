import yaml


class ConfigurationManager:
    @staticmethod
    def get_configuration(key: str):
        with open("config.yaml", 'r') as stream:
            config = yaml.safe_load(stream)

        if key not in config:
            raise Exception(f'{key} not defined in configuration')

        return config[key]