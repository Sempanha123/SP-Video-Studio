import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    implicitHeight: 170
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        SectionHeader { title: "Export Summary"; subtitle: root.controller && root.controller.summary.outputPath ? "Ready to review" : "Validate to see final output details" }
        RowLayout { Layout.fillWidth: true
            Text { text: root.controller && root.controller.summary.durationText ? "Duration  " + root.controller.summary.durationText : "Duration  —"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Text { text: root.controller && root.controller.summary.estimatedSizeText ? "Estimated  " + root.controller.summary.estimatedSizeText : "Estimated  —"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        }
        Text { Layout.fillWidth: true; text: root.controller && root.controller.summary.outputPath ? root.controller.summary.outputPath : "Output path will be resolved before export."; elide: Text.ElideMiddle; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Repeater {
            model: root.controller ? root.controller.validationIssues : []
            delegate: Text { required property var modelData; Layout.fillWidth: true; text: (modelData.severity === "error" ? "Error: " : "Note: ") + modelData.message; color: modelData.severity === "error" ? Theme.colors.danger : Theme.colors.warning; wrapMode: Text.WordWrap; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
    }
}
