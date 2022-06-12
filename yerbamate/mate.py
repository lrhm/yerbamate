import os
from argparse import ArgumentParser
import importlib
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import EarlyStopping
from types import SimpleNamespace
from torch import nn
from .logger import CustomLogger
import torch as t
import ipdb
import json
import sys
# TODO: find root recursively
# TODO:

class Mate:
    def __init__(self):
        self.root_folder = ""
        self.save_path = ""
        self.current_folder = os.path.dirname(__file__)
        self.__findroot()
        self.models = self.__list_packages("models")

    def __list_packages(self, folder: str):
        return (
            tuple(
                x
                for x in os.listdir(os.path.join(self.root_folder, folder))
                if not "__" in x
            )
            if os.path.exists(os.path.join(self.root_folder, folder))
            else tuple()
        )

    def __findroot(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        cur_folder = os.path.dirname(__file__)
        current_path = os.getcwd()
        self.root_folder = os.path.basename(current_path)
        os.chdir("..")
        sys.path += '.'

    def __load_model_class(self, model_name: str, folder="models"):
        return  __import__(
            f"{self.root_folder}.{folder}.{model_name}.model",
            fromlist=[folder],
        ).Model

    def __load_logger_class(self):
        #sys.path += self.current_folder
        #return __import__(f"{self.current_folder}.logger", fromlist=['logger']).CustomLogger
        return CustomLogger

    def __load_data_loader_class(self, data_loader_name: str):
        return __import__(
            f"{self.root_folder}.data_loader.{data_loader_name}",
            fromlist=['data_loader']
        ).CustomDataModule

    def __set_save_path(self, model_name: str):
        self.save_path = os.path.join(self.root_folder, "models", model_name)

    def __read_parameters(self, model_name: str):
        with open(
            os.path.join(
                self.root_folder, "models", model_name, "parameters.json"
            )
        ) as f:
            params = json.load(f)
        return SimpleNamespace(**params)

    def __get_trainer(self, model_name: str):
        params = self.__read_parameters(model_name)
        params.save_path = os.path.join(self.root_folder, "models", model_name)
        model = self.__load_model_class(model_name)(params)
        data_module = self.__load_data_loader_class(params.data_loader)(
            params
        )
        logger_module = self.__load_logger_class()
        return (
            Trainer(
                max_epochs=params.max_epochs,
                gpus=(1 if params.cuda else None),
                callbacks=[
                    EarlyStopping(
                        monitor="val_loss",
                        patience=params.early_stopping_patience,
                    ),
                    # checkpoint_callback,
                ],
                logger=logger_module(params),
                enable_checkpointing=False,
            ),
            model,
            data_module,
        )

    def __load_model(self, checkpoint_path: str, model: nn.Module):
        if os.path.exists(checkpoint_path):
            print(f"\nLoading model from checkpoint:'{checkpoint_path}'\n")
            model.load_state_dict(t.load(checkpoint_path))
        else:
            raise Exception(
                "No checkpoint found. You must train the model first!"
            )

    def init(self):
        pass

    def create(self, path: str):
        pass

    def remove(self, model_name: str):
        action = "go"
        while action not in ("y", "n"):
            action = input(
                f'Are you sure you want to remove model "{model_name}"? (y/n)\n'
            )
        if action == "y":
            os.system(
                f"rm -r {os.path.join(self.root_folder, 'models', model_name)}"
            )
            print(f"Removed model {model_name}")
        else:
            print("Ok, exiting.")

    def list(self, folder: str):
        print(
            "\n".join(
                tuple("\t" + str(m) for m in self.__list_packages(folder))
            )
        )

    def clone(self, source_model: str, target_model: str):
        os.system(
            f"cp -r {os.path.join(self.root_folder, 'models', source_model)} {os.path.join(self.root_folder, 'models', target_model)}"
        )

    def __fit(self, model_name: str):
        trainer, model, data_module = self.__get_trainer(model_name)
        trainer.fit(model, datamodule=data_module)

    def train(self, model_name: str):
        assert (
            model_name in self.models
        ), f'Model "{model_name}" does not exist.'

        save_path = os.path.join(self.root_folder, "models", model_name)
        checkpoint_path = os.path.join(save_path, "checkpoint.pt")
        action = "go"
        if os.path.exists(checkpoint_path):
            while action not in ("y", "n", ""):
                action = input(
                    "Checkpiont file exists. Re-training will erase it. Continue? ([y]/n)\n"
                )
            if action in ("y", ""):
                os.remove(checkpoint_path)
            else:
                print("Ok, exiting.")
                return
        self.__fit(model_name)

    def test(self, model_name: str):
        trainer, model, data_module = self.__get_trainer(model_name)
        trainer.test(model, datamodule=data_module)

    def restart(self, model_name: str):
        self.__fit(model_name)

    def tune(self, model: str, params: tuple[str, ...]):
        pass

    def exec(self, model: str, file: str = ""):
        pass
