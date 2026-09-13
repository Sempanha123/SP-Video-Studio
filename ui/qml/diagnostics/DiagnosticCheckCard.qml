import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var resultData: ({})
    signal detailsRequested(var resultData)
    signal actionRequested(string action)
    Layout.fillWidth: true
    implicitHeight: body.implicitHeight + Theme.spacing.lg * 2

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: root.resultData.name || "Check"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { text: root.resultData.category || ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            StatusBadge { text: String(root.resultData.status || "checking").replaceAll("_", " "); status: root.resultData.status || "checking" }
        }
        Text {
            Layout.fillWidth: true
            text: root.resultData.summary || ""
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            SecondaryButton { text: "Details"; compact: true; onClicked: root.detailsRequested(root.resultData) }
            SecondaryButton {
                visible: !!(root.resultData.metadata && root.resultData.metadata.action)
                text: "Fix / Open"
                compact: true
                onClicked: root.actionRequested(String(root.resultData.metadata.action || ""))
            }
            Item { Layout.fillWidth: true }
            Text { text: (root.resultData.durationMs || 0) + " ms"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
    }
}
