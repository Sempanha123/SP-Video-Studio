import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

RowLayout {
    id: root
    property var controller
    property var editor
    signal importRequested()
    signal exportRequested()
    spacing: Theme.spacing.sm

    SecondaryButton { text: "Undo"; compact: true; enabled: root.editor && root.editor.canUndo; onClicked: root.editor.undo() }
    SecondaryButton { text: "Redo"; compact: true; enabled: root.editor && root.editor.canRedo; onClicked: root.editor.redo() }
    Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 24; color: Theme.colors.border }
    SecondaryButton { text: "Import TXT"; iconName: "import"; compact: true; onClicked: root.importRequested() }
    SecondaryButton { text: "Export TXT"; iconName: "export"; compact: true; onClicked: root.exportRequested() }
    SecondaryButton { text: "Copy Full Script"; iconName: "copy"; compact: true; onClicked: if (root.controller) root.controller.copyFullScript() }
    Item { Layout.fillWidth: true }
    AppButton { text: "Save"; compact: true; enabled: root.controller && root.controller.dirty; onClicked: if (root.controller) root.controller.save() }
}
