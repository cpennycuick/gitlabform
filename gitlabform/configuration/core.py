import os
import textwrap

from logging import debug
from cli_ui import debug as verbose
from cli_ui import fatal

import yaml
from pathlib import Path
from mergedeep import merge
from gitlabform import EXIT_INVALID_INPUT


class ConfigurationCore:

    config = None
    config_dir = None

    def __init__(self, config_path=None, config_string=None):
        self._load_config(config_path=config_path, config_string=config_string)
        self._find_almost_duplicates()

    def get(self, path, default=None):
        """
        :param path: "path" to given element in YAML file, for example for:

        group_settings:
          sddc:
            deploy_keys:
              qa_puppet:
                key: some key...
                title: some title...
                can_push: false

        ..a path to a single element array ['qa_puppet'] will be: "group_settings|sddc|deploy_keys".

        To get the dict under it use: get("group_settings|sddc|deploy_keys")

        :param default: the value to return if the key is not found. The default 'None' means that an exception
                        will be raised in such case.
        :return: element from YAML file (dict, array, string...)
        """
        tokens = path.split("|")
        current = self.config

        try:
            for token in tokens:
                current = current[token]
        except:
            if default is not None:
                return default
            else:
                raise KeyNotFoundException

        return current

    def get_group_config(self, group) -> dict:
        """
        :param group: group/subgroup
        :return: configuration for this group/subgroup or empty dict if not defined,
                 ignoring the case
        """
        try:
            return self.get_case_insensitively(
                self.get("projects_and_groups"), f"{group}/*"
            )
        except KeyNotFoundException:
            return {}

    def get_project_config(self, group_and_project) -> dict:
        """
        :param group_and_project: 'group/project'
        :return: configuration for this project or empty dict if not defined,
                 ignoring the case
        """
        try:
            return self.get_case_insensitively(
                self.get("projects_and_groups"), group_and_project
            )
        except KeyNotFoundException:
            return {}

    def get_common_config(self) -> dict:
        """
        :return: literal common configuration or empty dict if not defined
        """
        return self.get("projects_and_groups|*", {})

    def is_project_skipped(self, project) -> bool:
        """
        :return: if project is defined in the key with projects to skip,
                 ignoring the case
        """
        return self.is_skipped_case_insensitively(
            self.get("skip_projects", []), project
        )

    def is_group_skipped(self, group) -> bool:
        """
        :return: if group is defined in the key with groups to skip,
                 ignoring the case
        """
        return self.is_skipped_case_insensitively(
            self.get("skip_groups", []), group
        )

    def get_case_insensitively(self, a_dict: dict, a_key: str):
        for dict_key in a_dict.keys():
            if dict_key.lower() == a_key.lower():
                return a_dict[dict_key]
        raise KeyNotFoundException()

    def is_skipped_case_insensitively(self, an_array: list, item: str) -> bool:
        """
        :return: if item is defined in the list to be skipped
        """
        item = item.lower()

        for list_element in an_array:
            list_element = list_element.lower()

            if list_element == item:
                return True

            if (
                list_element.endswith("/*")
                and item.startswith(list_element[:-2])
                and len(item) >= len(list_element[:-2])
            ):
                return True

        return False

    @staticmethod
    def merge_configs(more_general_config, more_specific_config) -> dict:
        """
        :return: merge more general config with more specific configs.
                 More specific config values take precedence over more general ones.
        """
        return dict(merge({}, more_general_config, more_specific_config))

    def _load_config(self, config_string=None, config_path=None):
        if config_path and config_string:
            fatal(
                "Please initialize with either config_path or config_string, not both.",
                exit_code=EXIT_INVALID_INPUT,
            )

        try:
            if config_string:
                verbose("Reading config from provided string.")
                self.config = yaml.safe_load(textwrap.dedent(config_string))
                self.config_dir = "."
            else:  # maybe config_path
                if "APP_HOME" in os.environ:
                    # using this env var should be considered unofficial, we need this temporarily
                    # for backwards compatibility. support for it may be removed without notice, do not use it!
                    config_path = os.path.join(os.environ["APP_HOME"], "config.yml")
                elif not config_path:
                    # this case is only meant for using gitlabform as a library
                    config_path = os.path.join(
                        str(Path.home()), ".gitlabform", "config.yml"
                    )
                elif config_path in [os.path.join(".", "config.yml"), "config.yml"]:
                    # provided points to config.yml in the app current working dir
                    config_path = os.path.join(os.getcwd(), "config.yml")

                verbose(f"Reading config from file: {config_path}")

                with open(config_path, "r") as ymlfile:
                    self.config = yaml.safe_load(ymlfile)
                    debug("Config parsed successfully as YAML.")

                # we need config path for accessing files for relative paths
                self.config_dir = os.path.dirname(config_path)

                if self.config.get("example_config"):
                    fatal(
                        "Example config detected, aborting.\n"
                        "Haven't you forgotten to use `-c <config_file>` parameter?\n"
                        "If you created your config based on the example config.yml,"
                        " then please remove 'example_config' key.",
                        exit_code=EXIT_INVALID_INPUT,
                    )

                if self.config.get("config_version", 1) != 2:
                    fatal(
                        "This version of GitLabForm requires 'config_version: 2' entry in the config.\n"
                        "This ensures that when the application behavior changes in a backward incompatible way,"
                        " you won't apply unexpected configuration to your GitLab instance.\n"
                        "Please read the upgrading guide here: https://bit.ly/3ub1g5C\n",
                        exit_code=EXIT_INVALID_INPUT,
                    )

                # we are NOT checking for the existence of non-empty 'projects_and_groups' key here
                # as it would break using GitLabForm as a library

        except (FileNotFoundError, IOError):
            raise ConfigFileNotFoundException(config_path)

        except Exception as e:
            raise ConfigInvalidException(e)

    def _find_almost_duplicates(self):

        # in GitLab groups and projects names are de facto case insensitive:
        # you can change the case of both name and path BUT you cannot create
        # 2 groups which names differ only with case and the same thing for
        # projects. therefore we cannot allow such entries in the config,
        # as they would be ambiguous.

        for path in [
            "projects_and_groups",
            "skip_groups",
            "skip_projects",
        ]:
            if self.get(path, 0):
                almost_duplicates = self._find_almost_duplicate(path)
                if almost_duplicates:
                    fatal(
                        f"There are almost duplicates in the keys of {path} - they differ only in case.\n"
                        f"They are: {', '.join(almost_duplicates)}\n"
                        f"This is not allowed as we ignore the case for group and project names.",
                        exit_code=EXIT_INVALID_INPUT,
                    )

    def _find_almost_duplicate(self, configuration_path):
        """
        Checks given configuration key and reads its keys - if it is a dict - or elements - if it is a list.
        Looks for items that are almost the same - they differ only in the case.
        :param configuration_path: configuration path, f.e. "group_settings"
        :return: list of items that have almost duplicates,
                 or an empty list if none are found
        """

        dict_or_list = self.get(configuration_path)
        if isinstance(dict_or_list, dict):
            items = dict_or_list.keys()
        else:
            items = dict_or_list

        items_with_lowercase_names = [x.lower() for x in items]

        # casting these to sets will deduplicate the one with lowercase names
        # lowering its cardinality if there were elements in it
        # that before lowering differed only in case
        if len(set(items)) != len(set(items_with_lowercase_names)):

            # we have some almost duplicates, let's find them
            almost_duplicates = []
            for first_item in items:
                occurrences = 0
                for second_item in items_with_lowercase_names:
                    if first_item.lower() == second_item.lower():
                        occurrences += 1
                        if occurrences == 2:
                            almost_duplicates.append(first_item)
                            break
            return almost_duplicates

        else:
            return []


class ConfigFileNotFoundException(Exception):
    pass


class ConfigInvalidException(Exception):
    def __init__(self, underlying: Exception):
        self.underlying = underlying


class KeyNotFoundException(Exception):
    pass
