import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
import "../WorkflowData.js" as WorkflowData

Item {
    id: root
    property string selectedWorkflow: "news"
    signal toastRequested(string message, string variant)

    function accentFor(name) {
        if (name === "news") return Theme.colors.news
        if (name === "story") return Theme.colors.story
        if (name === "translate") return Theme.colors.translate
        if (name === "video") return Theme.colors.video
        if (name === "shorts") return Theme.colors.shorts
        return Theme.colors.batch
    }
    function modeObject() {
        for (var i = 0; i < WorkflowData.modes.length; ++i)
            if (WorkflowData.modes[i].key === selectedWorkflow) return WorkflowData.modes[i]
        return WorkflowData.modes[0]
    }

    ScrollView {
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: Theme.spacing.xl
            ColumnLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
                Text { text: "Create New Video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Choose how you want to start."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            GridLayout {
                Layout.fillWidth: true; columns: width < 840 ? 2 : 3; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                Repeater { model: WorkflowData.modes
                    delegate: CreateModeCard {
                        required property var modelData
                        Layout.fillWidth: true; Layout.minimumWidth: 210
                        title: modelData.title; description: modelData.description; iconName: modelData.icon; mode: modelData.key
                        accentColor: root.accentFor(modelData.accent)
                        selected: root.selectedWorkflow === modelData.key
                        onClicked: root.selectedWorkflow = modelData.key
                    }
                }
            }
            AppCard {
                Layout.fillWidth: true; Layout.preferredHeight: 132
                RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.lg
                    Rectangle { width: 42; height: 42; radius: Theme.radius.large; color: Theme.colors.accentSoft; Icon { anchors.centerIn: parent; width: 21; height: 21; name: root.modeObject().icon } }
                    ColumnLayout { Layout.fillWidth: true; spacing: 3
                        Text { text: "Workflow"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        Text { text: root.modeObject().title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: root.modeObject().description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    AppButton { text: "Continue"; iconName: "arrow-right"; onClicked: root.toastRequested("Workflow setup will be available in a later phase.", "info") }
                }
            }
        }
    }
}
