from denite.kind.file import Kind as File


class Kind(File):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = "autocmd"

        self.redraw_actions += ["remove"]
        self.persist_actions += ["remove"]

    def action_remove(self, context):
        for target in context["targets"]:
            group = target["action__autocmd_group"]
            event = target["action__autocmd_event"]
            pattern = target["action__autocmd_pattern"]
            self.vim.command(f"autocmd! {group} {event} {pattern}")

    def action_delete(self, context):
        self.action_remove(context)
