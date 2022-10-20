import os

import sys, inspect

from ..sources.local import LocalDataSource

from .metadata import BaseMetadata, Metadata

from ..package import Package
from bombilla import Bombilla
import ipdb

from .utils import get_function_args, find_in_bombilla_dict


class ModuleMetadataGenerator:
    def __init__(
        self,
        module_paths: list[str],
        base_metadata: Metadata,
        local_data_source: LocalDataSource,
    ):

        self.root_module = module_paths[0]
        self.type_module = module_paths[1]
        # self.local_module = module_paths[-1]

        self.module_paths = module_paths

        self.base_metadata = base_metadata.copy()
        self.base_metadata.update(module_path=module_paths[1:], root_module=None)
        self.local_data_source = local_data_source

        self.module_path = os.path.join(*module_paths)

        self.module = ".".join(module_paths)

        self.local_module = ".".join(module_paths[1:])

        self.module_files = os.listdir(os.path.join(*module_paths))

    def get_possible_modules(self):
        return [
            self.module,
            # ".".join([self.root_module, self.type_module, self.local_module]),
            # ".".join([self.type_module, self.local_module]),
        ]

    def search_experiments_for_defaults(self, module, function_name):

        experiments = self.local_data_source.list("experiments")

        samples = []

        for experiment in experiments:

            conf, _ = self.local_data_source.load_experiment(experiment)
            # ipdb.set_trace()

            sample = find_in_bombilla_dict(conf, module, function_name)
            if sample:
                samples += [{"sample": sample, "experiment": conf}]

        return samples

    def update_metadata(self):

        # update URL to point to the right module
        # addition = self.module_paths + [""]
        url_addition = "/".join(self.module_paths + [""])
        new_url = self.base_metadata.url + url_addition
        type = self.type_module
        self.base_metadata.update(url=new_url, type=type)

    def generate(self):

        self.module = self.__get_local_module()

        classes = self.__find_classes(self.module)

        meta = [self.generate_class_metadata(klass) for klass in classes]

        functions = self.__find_functions(self.module)

        fun_meta = [self.generate_function_metadata(function) for function in functions]

        self.update_metadata()
        results = {
            "exports": {
                "classes": meta,
                "functions": fun_meta,
            }
        }
        self.base_metadata.add(**results)

        self.save_metadata()

        return self.base_metadata

    def save_metadata(self):

        json_path = os.path.join(self.module_path, "metadata.json")

        with open(json_path, "w") as f:
            f.write(str(self.base_metadata))

    def format_modules(self, args: dict) -> dict:

        res = args.copy()
        for key, value in args.items():
            if type(value) == dict and "module" in value:

                # shorterns the module name
                value["module"] = value["module"].replace(
                    ".".join([self.root_module, self.type_module, ""]), ""
                )
                res[key] = value

        return res

    def generate_class_metadata(self, klass):

        # ipdb.set_trace()
        args, errors = get_function_args(klass[1].__init__, {})
        args = self.format_modules(args)

        defualts = self.search_experiments_for_defaults(klass[1], klass[0])

        result = {
            "class_name": klass[0],
            "module": self.local_module,
            "params": args,
            "samples": defualts,
            "errors": errors,
        }

        # remove non and empty values
        result = {k: v for k, v in result.items() if v and v != "None" and v != []}

        return result

    def generate_function_metadata(self, function):
        args, errors = get_function_args(function[1], {})
        args = self.format_modules(args)

        defualts = self.search_experiments_for_defaults(function[1], function[0])

        result = {
            "function_name": function[0],
            "module": self.local_module,
            "params": args,
            "samples": defualts,
            "errors": errors,
        }

        # remove non and empty values
        result = {k: v for k, v in result.items() if v and v != "None" and v != []}

        return result

    def __get_local_module(self):
        return __import__(
            f"{self.module}",
            fromlist=[self.module_paths[-1]],
        )

    def __find_functions(self, module):

        return inspect.getmembers(module, inspect.isfunction)

    def __find_classes(self, module):

        return inspect.getmembers(module, inspect.isclass)
