from bokeh.models import Tool
from bokeh.core.properties import String

JS_CODE_SAVE = """
import * as p from "core/properties"
import {ActionTool, ActionToolView} from "models/tools/actions/action_tool"

export class NewSaveView extends ActionToolView

  # this is executed when the button is clicked
  doit: () ->
    @plot_view.save(@model.save_name)

export class CustomSaveTool extends ActionTool
  default_view: NewSaveView
  type: "CustomSaveTool"

  tool_name: "Save"
  icon: "bk-tool-icon-save"

  @define { save_name: [ p.String ] } """

class SaveTool(Tool):
    """
    Save a plot with a custom name.
    Usage: CustomSaveTool(save_name = name)
    """
    __implementation__ = JS_CODE_SAVE
    save_name = String()