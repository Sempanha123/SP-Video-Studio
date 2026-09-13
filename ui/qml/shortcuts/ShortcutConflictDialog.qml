import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    width: 470
    header: null
    footer: null
    modal: true
    property string message: ""
    property string sequence: ""

    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text {
            text: "Shortcut conflict"
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.heading
            font.weight: Theme.type.semibold
        }
        Text {
            Layout.fillWidth: true
            text: root.message
            wrapMode: Text.WordWrap
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.body
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton {
                text: "Cancel"
                onClicked: { Shortcuts.cancelConflict(); root.close() }
            }
            AppButton {
                text: "Replace"
                onClicked: {
                    if (Shortcuts.replaceConflict()) root.close()
                }
            }
        }
    }
}
