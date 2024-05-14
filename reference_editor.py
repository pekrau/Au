"Reference editor; also to view abstract and notes."

from icecream import ic

from text_editor import BaseEditor


class ReferenceEditor(BaseEditor):
    "Edit a reference."

    def __init__(self, main, text):
        super().__init__(main.root, main, text)
        self.toplevel_setup()
        self.menubar_setup()
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        self.render(self.text.ast)
        self.view.edit_modified(False)

    def close_finalize(self):
        "Perform action at window closing time."
        self.main.reference_editors.pop(self.text.fullname)

