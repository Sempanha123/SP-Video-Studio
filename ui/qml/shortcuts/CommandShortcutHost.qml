import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Commands 1.0

Item {
    id: root
    visible: false
    width: 0; height: 0
    Repeater {
        model: Commands.shortcutBindings
        delegate: Item {
            required property var modelData
            width: 0; height: 0
            Shortcut {
                sequence: modelData.shortcut || ""
                context: Qt.ApplicationShortcut
                enabled: Commands.revision >= 0 && Commands.shortcutBindingEnabled(modelData.id, modelData.shortcut)
                onActivated: Commands.trigger(modelData.id)
            }
        }
    }
}
