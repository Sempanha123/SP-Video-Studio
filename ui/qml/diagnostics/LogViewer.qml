import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Diagnostics 1.0
import "../theme"
import "../components"

Item {
    id: root
    property string selectedText: ""
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Recent bounded logs"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Item { Layout.fillWidth: true }
            AppComboBox {
                Layout.preferredWidth: 150
                model: ["Error", "Warning", "Info", "Debug", "All"]
                Component.onCompleted: currentIndex = Math.max(0, ["error","warning","info","debug","all"].indexOf(Diagnostics.logSeverity))
                onActivated: Diagnostics.setLogSeverity(String(currentText).toLowerCase())
            }
            SecondaryButton { text: "Refresh"; compact: true; onClicked: Diagnostics.refreshLogs() }
            SecondaryButton { text: "Open Logs Folder"; compact: true; onClicked: Diagnostics.openLogsFolder() }
        }
        InfoBanner { Layout.fillWidth: true; text: "Only a recent bounded subset is loaded. Credentials and personal path prefixes are sanitized before display/copy." }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.spacing.xs
            model: Diagnostics.logs
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: Math.max(54, logText.implicitHeight + Theme.spacing.md * 2)
                radius: Theme.radius.medium
                color: mouse.containsMouse ? Theme.colors.surfaceHover : Theme.colors.surface
                border.color: Theme.colors.border
                Text {
                    id: logText
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.md
                    text: "[" + String(modelData.severity || "info").toUpperCase() + "] " + (modelData.message || "")
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.caption
                    wrapMode: Text.WrapAnywhere
                }
                MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.selectedText = modelData.message || "" }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { text: "Copy Selected"; enabled: root.selectedText.length > 0; onClicked: Diagnostics.copyText(root.selectedText) }
            Item { Layout.fillWidth: true }
            Text { text: Diagnostics.logs.length + " line(s) loaded"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
    }
}
