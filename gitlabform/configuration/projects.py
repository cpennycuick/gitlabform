from logging import debug

from gitlabform.configuration.core import ConfigurationCore
from gitlabform.configuration.groups import ConfigurationGroups


class ConfigurationProjects():

    def __init__(self, config: ConfigurationCore, groups: ConfigurationGroups):
        self.config = config
        self.groups = groups

    def get_projects(self) -> list:
        """
        :return: sorted list of projects names, that are EXPLICITLY defined in the config
        """
        projects = []
        projects_and_groups = self.config.get("projects_and_groups")
        for element in projects_and_groups.keys():
            if element != "*" and not element.endswith("/*"):
                projects.append(element)
        return sorted(projects)

    def get_effective_config_for_project(self, group_and_project) -> dict:
        """
        :param group_and_project: "project_group/project_name"
        :return: merged configuration for this project, from common, group/subgroup and project level.
                 If project belongs to a subgroup, like "x/y/z", then it gets config from both group "x" as well
                 as subgroup "y".
                 Merging is additive.
        """

        common_config = self.config.get_common_config()
        debug("Common config: %s" % common_config)

        group, project = group_and_project.rsplit("/", 1)
        if "/" in group:
            group_config = self.groups.get_effective_subgroup_config(group)
        else:
            group_config = self.config.get_group_config(group)
        debug("Effective group/subgroup config: %s" % group_config)

        project_config = self.config.get_project_config(group_and_project)
        debug("Project config: %s" % project_config)

        common_and_group_config = self.config.merge_configs(common_config, group_config)
        debug("Effective config common+group/subgroup: %s" % common_and_group_config)

        effective_config = self.config.merge_configs(common_and_group_config, project_config)
        debug("Effective config common+group/subgroup+project: %s" % effective_config)

        return effective_config


class EmptyConfigException(Exception):
    pass
