from logging import debug

from gitlabform.configuration.projects import ConfigurationProjects
from gitlabform.configuration.groups import ConfigurationGroups
from gitlabform.configuration.core import ConfigurationCore


# note that we are NOT using mixins here, but only the most advanced subclass
# class Configuration(ConfigurationCaseInsensitiveProjectsAndGroups):
#     pass

class Configuration(ConfigurationCore):

    groups: ConfigurationGroups
    projects: ConfigurationProjects

    def __init__(self, config_path=None, config_string=None):
        super().__init__(config_path=config_path, config_string=config_string)

        self.groups = ConfigurationGroups(self)
        self.projects = ConfigurationProjects(self, self.groups)

    def get_groups(self) -> list:
        return self.groups.get_groups()

    def get_effective_config_for_group(self, group) -> dict:
        return self.groups.get_effective_config_for_group(group)

    def get_effective_subgroup_config(self, subgroup) -> dict:
        return self.groups.get_effective_subgroup_config(subgroup)

    def get_projects(self) -> list:
        return self.projects.get_projects()

    def get_effective_config_for_project(self, group_and_project) -> dict:
        return self.projects.get_effective_config_for_project(group_and_project)

