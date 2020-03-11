import re
from collections import UserDict
from itertools import chain

from .base import Base


class Source(Base):

    EVENT_KEY = "event"
    GROUP_KEY = "group"
    FILE_TYPE_KEY = "file_type"
    CMD_KEY = "cmd"
    FILE_PATH_KEY = "file_path"
    LINE_NUMBER_KEY = "line_number"

    NONE_GROUP_NAME = "None_Group"
    WORD_FORMAT = "{group} {event} {file_type} {cmd}"

    event_pattern = re.compile("^(?P<{event}>\\S+)$".format(event=EVENT_KEY))
    group_event_pattern = re.compile(
        "^(?P<{group}>\\S+)\\s+(?P<{event}>\\w+)".format(
            group=GROUP_KEY, event=EVENT_KEY
        )
    )
    file_type_cmd_pattern = re.compile(
        "^    (?P<{file_type}>\\S+)\\s+(?P<{cmd}>.+)".format(
            file_type=FILE_TYPE_KEY, cmd=CMD_KEY
        )
    )
    file_type_pattern = re.compile(
        "^    (?P<{file_type}>\\S+)$".format(file_type=FILE_TYPE_KEY)
    )
    cmd_pattern = re.compile("^              (?P<{cmd}>.+)".format(cmd=CMD_KEY))
    file_path_pattern = re.compile(
        "^\\t(\\S+ )+(?P<{file_path}>\\S+)\\s+line\\s+(?P<{line_number}>\\d+)$".format(
            file_path=FILE_PATH_KEY, line_number=LINE_NUMBER_KEY
        )
    )

    escape = str.maketrans(
        {
            "*": "\\*",
            ".": "\\.",
            "(": "\\(",
            ")": "\\)",
            "|": "\\|",
            "&": "\\&",
            "=": "\\=",
            "<": "\\<",
            ">": "\\>",
            "{": "\\{",
            "}": "\\}",
            "%": "\\%",
            "+": "\\+",
            "/": "\\/",
            "$": "\\$",
            "^": "\\^",
            "@": "\\@",
            "?": "\\?",
            "~": "\\~",
        }
    )

    def __init__(self, vim):
        super().__init__(vim)

        self.name = "autocmd"
        self.kind = "file"
        self.matchers = ["matcher_regexp"]
        self.sorters = []

        self.current_group_name = ""
        self.current_event_name = ""
        self.current_file_type = ""
        self.current_cmd = ""

    def gather_candidates(self, context):
        autocmd_result = self.vim.call("denite_autocmd#util#redir", "verbose autocmd")
        self.autocmd_groups = AutocmdGroups()
        self.parse((x for x in autocmd_result.split("\n")[1:]))
        return [
            {
                "word": self.WORD_FORMAT.format(
                    group=autocmd.group_name
                    if autocmd.group_name != ""
                    else self.NONE_GROUP_NAME,
                    event=autocmd.event_name,
                    file_type=autocmd.file_type,
                    cmd=autocmd.cmd,
                ),
                "action__path": autocmd.file_path,
                "action__line": autocmd.line_number,
            }
            for autocmd in self.autocmd_groups.get_autocmds()
        ]

    def parse(self, line_generator):
        while True:
            try:
                line = next(line_generator)
                match_result = self.event_pattern.match(line)
                if match_result:
                    self.parse_event(match_result)
                    continue
                match_result = self.group_event_pattern.match(line)
                if match_result:
                    self.parse_group_event(match_result)
                    continue
                match_result = self.file_type_cmd_pattern.match(line)
                if match_result:
                    self.parse_file_type_cmd(match_result, line_generator)
                    continue
                match_result = self.file_type_pattern.match(line)
                if match_result:
                    self.parse_file_type(match_result, line_generator)
                    continue
                match_result = self.cmd_pattern.match(line)
                if match_result:
                    self.parse_cmd(match_result, line_generator)
                    continue
            except StopIteration:
                break

    def parse_event(self, match_result):
        self.current_group_name = ""
        self.current_event_name = match_result.group(self.EVENT_KEY)
        self.current_file_type = ""
        self.current_cmd = ""

    def parse_group_event(self, match_result):
        self.parse_event(match_result)
        self.current_group_name = match_result.group(self.GROUP_KEY)

    def parse_file_type(self, match_result, line_generator):
        self.current_file_type = match_result.group(self.FILE_TYPE_KEY)
        match_result = self.cmd_pattern.match(next(line_generator))
        if match_result:
            self.parse_cmd(match_result, line_generator)

    def parse_cmd(self, match_result, line_generator):
        self.current_cmd = match_result.group(self.CMD_KEY)
        match_result = self.file_path_pattern.match(next(line_generator))
        if match_result:
            self.parse_position(match_result)

    def parse_file_type_cmd(self, match_result, line_generator):
        self.current_file_type = match_result.group(self.FILE_TYPE_KEY)
        self.parse_cmd(match_result, line_generator)

    def parse_position(self, match_result):
        file_path = match_result.group(self.FILE_PATH_KEY)
        line_number = match_result.group(self.LINE_NUMBER_KEY)
        self.autocmd_groups.add_autocmd(
            self.current_group_name,
            self.current_event_name,
            self.current_file_type,
            self.current_cmd,
            file_path,
            line_number,
        )


class AutocmdGroups(UserDict):
    def add_autocmd(
        self, group_name, event_name, file_type, cmd, file_path, line_number
    ):
        autocmd = Autocmd(
            group_name, event_name, file_type, cmd, file_path, line_number
        )
        try:
            autocmd_group = self[group_name]
        except KeyError:
            autocmd_group = AutocmdGroup(group_name)
            self[group_name] = autocmd_group
        autocmd_group.add_autocmd(autocmd)

    def get_autocmds(self):
        autocmds = []
        extend = autocmds.extend
        for autocmd_group in self.values():
            extend(autocmd_group.values())
        return list(chain.from_iterable(autocmds))


class AutocmdGroup(UserDict):
    def __init__(self, group_name):
        super().__init__()
        self.group_name = group_name

    def add_autocmd(self, autocmd):
        try:
            autocmds = self[autocmd.event_name]
        except KeyError:
            autocmds = []
            self[autocmd.event_name] = autocmds
        autocmds.append(autocmd)


class Autocmd(object):
    def __init__(self, group_name, event_name, file_type, cmd, file_path, line_number):
        self.group_name = group_name
        self.event_name = event_name
        self.file_type = file_type
        self.cmd = cmd
        self.file_path = file_path
        self.line_number = line_number
