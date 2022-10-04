from .source import DataSource
import os
from typing import Optional


class LocalDataSource(DataSource):
    def __init__(self, root_dir: str = "."):
        super().__init__()
        assert "mate.json" in os.listdir(
            root_dir
        ), "No mate.json found in root directory. Check this is a valid mate project."
        self.models = self.__filter_regular_folders(
            os.listdir(os.path.join(root_dir, "models"))
        )
        self.trainers = self.__filter_regular_folders(
            os.listdir(os.path.join(root_dir, "trainers"))
        )
        self.data_loaders = self.__filter_regular_folders(
            os.listdir(os.path.join(root_dir, "data_loaders"))
        )
        self.experiments = os.listdir(os.path.join(root_dir, "experiments"))
        self.packages = []  # TODO: what's this?

    def __filter_regular_folders(self, names: list[str]):
        return [fn for fn in names if not fn in ["__pycache__", "__init__.py"]]

    def __filter_names(self, query: Optional[str], names: list[str]):
        return names if query is None else [name for name in names if query == name]

    def get_models(self, query: Optional[str] = None):
        return self.__filter_names(query, self.models)

    def get_trainers(self, query: Optional[str] = None):
        return self.__filter_names(query, self.trainers)

    def get_data_loaders(self, query: Optional[str] = None):
        return self.__filter_names(query, self.data_loaders)

    def get_experiments(self, query: Optional[str] = None):
        return self.__filter_names(query, self.experiments)

    def get_packages(self, query: Optional[str] = None):
        return self.packages

    def add_model(self, model):
        self.models.append(model)

    def add_trainer(self, trainer):
        self.trainers.append(trainer)

    def add_data_loader(self, dataset):
        self.data_loaders.append(dataset)

    def add_experiment(self, experiment):
        self.experiments.append(experiment)

    def add_package(self, package):
        self.packages.append(package)
