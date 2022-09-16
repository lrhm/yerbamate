from curses.panel import new_panel
import os
from argparse import ArgumentParser, Namespace

from sre_constants import ASSERT
from pytorch_lightning import LightningModule, Trainer


from yerbamate.bunch import Bunch
from yerbamate.migrator import Migration

import ipdb
import json
import sys

import shutil


from yerbamate import utils, parser, io


class Mate:

    @staticmethod
    def init(project_name: str):
        # should actually be a package install
        pass

    def __init__(self, init=False):
        self.root_folder = ""
        self.save_path = ""
        self.current_folder = os.path.dirname(__file__)
        self.__findroot()
        self.__update_mate_version()
        self.models = self.__list_packages("models")
        self.is_restart = False
        self.run_params = None
        self.custom_save_path = None

    def __list_packages(self, folder: str):
        return io.list_packages(self.root_folder, folder)

    def __update_mate_version(self):
        utils.migrate_mate_version(self.config, self.root_folder)

    def __findroot(self):
        """
        Method in charge of finding the root folder of the project and reading the content of mate.json
        """
        self.root_folder, self.config = io.find_root()
        self.root_save_folder = self.config.results_folder

    def __load_lightning_module(
        self, model_name: str, params: Bunch, parameters_file_name: str
    ) -> LightningModule:

        model_class, pl_params = parser.parse_module_class_recursive(
            params.pytorch_lightning_module, base_module=f"{self.root_folder}.models.{model_name}", root_module=f"{self.root_folder}", map_key_values={
                "save_path": self.save_path, "save_dir": self.save_path})

        model = model_class(params=Namespace(**params), **pl_params)

        return model

    def __load_pl_trainer(
        self, model_name: str, params: Bunch, parameters_file_name: str
    ) -> Trainer:

        trainer_object = parser.parse_module_object(
            params.trainer, self.root_folder+".models."+model_name, self.root_folder, {"save_path": self.save_path, "save_dir": self.save_path})
        return trainer_object

    def __load_data_loader(self, params: Bunch):

        return parser.parse_module_object(params.data,
                                          base_module=f"{self.root_folder}.data",
                                          root_module=f"{self.root_folder}",
                                          map_key_values={
                                              "save_path": self.save_path, "save_dir": self.save_path}
                                          )

    def __load_exec_function(self, exec_file: str):
        return __import__(
            f"{self.root_folder}.exec.{exec_file}",
            fromlist=["exec"],
        ).run

    def __set_save_path(self, model_name: str, params: str):
        self.save_path = io.set_save_path(
            self.root_save_folder, self.root_folder, model_name, params)

    def __read_hyperparameters(self, model_name: str, hparams_name: str = "default"):

        return io.read_hyperparameters(self.config, self.root_folder, model_name, hparams_name)

    def __get_trainer(self, model_name: str, parameters: str):
        params = self.__read_hyperparameters(model_name, parameters)
        self.__set_save_path(model_name, parameters)
        params.save_path = self.save_path
        pl_module = self.__load_lightning_module(
            model_name, params, parameters)
        data_module = self.__load_data_loader(params)
        params.model_name = model_name

        if self.config.contains("print_model"):
            if self.config.print_model:
                print(pl_module)

        trainer = self.__load_pl_trainer(model_name, params, parameters)
        return (trainer, pl_module, data_module)

    def create(self, path: str):
        pass

    def remove(self, model_name: str):
        io.remove(self.root_folder, model_name)

    def list(self, folder: str):
        io.list(self.root_folder, folder)

    def clone(self, source_model: str, target_model: str):
        io.clone(self.root_folder, source_model, target_model)

    def snapshot(self, model_name: str):

        io.snapshot(self.root_folder, model_name)

    def __fit(self, model_name: str, params: str):
        trainer, model, data_module = self.__get_trainer(model_name, params)

        if self.is_restart:
            checkpoint_path = os.path.join(
                self.save_path, "checkpoints", "last.ckpt")
            trainer.fit(model, datamodule=data_module,
                        ckpt_path=checkpoint_path)
        else:
            trainer.fit(model, datamodule=data_module)
        # trainer.fit(model, datamodule=data_module)

    def train(self, model_name: str, parameters: str = "default"):
        assert model_name in self.models, f'Model "{model_name}" does not exist.'
        print(
            f"Training model {model_name} with hyperparameters: {parameters}.json")

        # we need to load hyperparameters before training to set save_path
        _ = self.__read_hyperparameters(model_name, parameters)
        self.__set_save_path(model_name, parameters)

        checkpoint_path = os.path.join(self.save_path, "checkpoint")
        if not os.path.exists(checkpoint_path):
            os.mkdir(checkpoint_path)
        checkpoints = [
            os.path.join(checkpoint_path, p) for p in os.listdir(checkpoint_path)
        ]
        action = "go"
        if len(checkpoints) > 0:
            while action not in ("y", "n", ""):
                action = input(
                    "Checkpiont file exists. Re-training will erase it. Continue? ([y]/n)\n"
                )
            if action in ("y", "", "Y"):
                for checkpoint in checkpoints:
                    os.remove(checkpoint)  # remove all checkpoint files
            else:
                print("Ok, exiting.")
                return

        self.__fit(model_name, parameters)

    def test(self, model_name: str, params: str):
        assert model_name in self.models, f'Model "{model_name}" does not exist.'
        params = "parameters" if params == "" or params == "None" else params
        print(
            f"Testing model {model_name} with hyperparameters: {params}.json")

        trainer, model, data_module = self.__get_trainer(model_name, params)

        checkpoint_path = os.path.join(
            self.save_path, "checkpoint", "best.ckpt")

        trainer.test(model, datamodule=data_module, ckpt_path=checkpoint_path)

    def restart(self, model_name: str, params: str):
        assert model_name in self.models, f'Model "{model_name}" does not exist.'
        params = "parameters" if params == "" or params == "None" else params
        print(f"Restarting model {model_name} with parameters: {params}.json")

        self.is_restart = True
        self.__fit(model_name, params)

    def tune(self, model: str, params: tuple[str, ...]):
        """
        Fine tunes specified hyperparameters. (Not implemented yet)
        """
        pass

    def add(self, model_name: str, repo: str):
        """
        Adds a dependency to a model.
        """
        mate_dir = ".mate"
        if not os.path.exists(mate_dir):
            os.makedirs(mate_dir, exist_ok=True)
        os.system(f"git clone {repo} {mate_dir}")

        conf = os.path.join(mate_dir, "mate.json")
        conf = Bunch(json.load(open(conf)))

        dest_dir = os.path.join(
            self.root_folder, "models", model_name, "modules")
        os.makedirs(dest_dir, exist_ok=True)

        shutil.copytree(os.path.join(mate_dir, conf.export), dest_dir)
        shutil.copytree(
            os.path.join(mate_dir, "mate.json"),
            os.path.join(dest_dir, conf.export),
        )
        shutil.rmtree(mate_dir)

        new_params = {}
        for model in conf.models:
            new_params[model["class_name"]] = model["params"]
        ipdb.set_trace()
        old_params_files = [
            os.path.join(self.root_folder, "models",
                         model_name, "hyperparameters", p)
            for p in os.listdir(
                os.path.join(self.root_folder, "models",
                             model_name, "hyperparameters")
            )
        ]
        for old_params_file in old_params_files:
            p = Bunch(json.load(open(old_params_file)))
            p.update(new_params)
            with open(old_params_file, "w") as f:
                json.dump(p, f, indent=4)
        print(f"Sucessfully added dependency to model {model_name}")

    def install(self, repo: str, source_model: str, destination_model: str):
        """
        installs a package
        """
        source_model_base_name = (
            source_model.split(
                ".")[-1] if "." in source_model else source_model
        )
        mate_dir = ".matedir"
        if not os.path.exists(mate_dir):
            os.mkdir(mate_dir)
        os.system(f"git clone {repo} {mate_dir}")
        os.system(
            f"mv {os.path.join(mate_dir, '*')} {os.path.join(destination_model, source_model_base_name)}"
        )
        new_parameters = utils.get_model_parameters(
            os.path.join(source_model, destination_model)
        )
        old_params_files = [
            os.path.join("hyperparameters", p) for p in os.listdir("hyperparameters")
        ]
        for old_params_file in old_params_files:
            params_name = old_params_file.split(".")[0]
            old_params = self.__read_hyperparameters(
                destination_model, params_name)
            old_params[source_model_base_name] = new_parameters
            with open(old_params_file, "w") as f:
                json.dump(old_params, f)

    def exec(self, model: str, params: str, exec_file: str):
        params = "parameters" if params == "" or params == "None" else params
        print(f"Executing model {model} with result of: {params}")
        _, model, _ = self.__get_trainer(model, params)

        self.__load_exec_function(exec_file)(model)

    def export(self):
        models = self.config.models
        for model in models:
            params = self.__populate_model_params(model)
            model["params"] = params
        # save params to mate.json
        with open("mate.json", "w") as f:
            json.dump(self.config, f, indent=4)

        print("Exported models to mate.json")

    def __export_model(self, model: str):
        export_root = os.path.join(self.root_folder, "export")

        pass

    def __populate_model_params(self, model: dict):
        export_root = self.config.export
        model = Bunch(model)

        model_class = __import__(
            f"{export_root}.{model.file}", fromlist=[model.file]
        ).__getattribute__(model.class_name)
        params = utils.get_function_parameters(model_class.__init__)

        # convert type class to strings
        for param in params:
            if isinstance(params[param], type):
                params[param] = str(params[param])

        return params
