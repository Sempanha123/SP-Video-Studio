import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
import "../WorkflowData.js" as WorkflowData

Item {
    id: root
    property string selectedWorkflow: "news"
    signal navigateRequested(string page, string workflow)
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
    function applyWorkflowDefaults() {
        var ratio = (selectedWorkflow === "news" || selectedWorkflow === "shorts") ? "9:16" : "16:9"
        ratioBox.currentIndex = ratioBox.model.indexOf(ratio)
    }
    function createProject() {
        if (projectName.text.trim().length === 0) {
            root.toastRequested("Enter a project name before creating the project.", "warning")
            projectName.forceActiveFocus()
            return
        }
        if (typeof projectController === "undefined") {
            root.toastRequested("Project services are not available.", "error")
            return
        }
        var languageCode = languageBox.currentIndex === 1 ? "km" : "en"
        var projectId = projectController.createProject(
            projectName.text.trim(),
            selectedWorkflow,
            languageCode,
            ratioBox.currentText,
            parseInt(fpsBox.currentText)
        )
        if (projectId !== "")
            root.navigateRequested("workspace", "")
    }

    onSelectedWorkflowChanged: applyWorkflowDefaults()
    Component.onCompleted: applyWorkflowDefaults()

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: Theme.spacing.xl

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing.xs
                Text { text: "Create New Video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Choose how you want to start, then set the basic project details."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width < 840 ? 2 : 3
                columnSpacing: Theme.spacing.lg
                rowSpacing: Theme.spacing.lg
                Repeater {
                    model: WorkflowData.modes
                    delegate: CreateModeCard {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.minimumWidth: 210
                        title: modelData.title
                        description: modelData.description
                        iconName: modelData.icon
                        mode: modelData.key
                        accentColor: root.accentFor(modelData.accent)
                        selected: root.selectedWorkflow === modelData.key
                        onClicked: root.selectedWorkflow = modelData.key
                    }
                }
            }

            AppCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 260
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.xl
                    spacing: Theme.spacing.lg

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacing.md
                        Rectangle {
                            width: 42; height: 42; radius: Theme.radius.large
                            color: Theme.colors.accentSoft
                            Icon { anchors.centerIn: parent; width: 21; height: 21; name: root.modeObject().icon }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { text: root.modeObject().title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                            Text { text: root.modeObject().description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: width < 760 ? 2 : 4
                        columnSpacing: Theme.spacing.md
                        rowSpacing: Theme.spacing.md

                        ColumnLayout {
                            Layout.columnSpan: width < 760 ? 2 : 1
                            Layout.fillWidth: true; spacing: Theme.spacing.xs
                            Text { text: "Project Name"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.label }
                            AppTextField { id: projectName; Layout.fillWidth: true; placeholderText: "My video project"; maximumLength: 120 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.xs
                            Text { text: "Language"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.label }
                            AppComboBox { id: languageBox; Layout.fillWidth: true; model: ["English", "Khmer"] }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.xs
                            Text { text: "Aspect Ratio"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.label }
                            AppComboBox { id: ratioBox; Layout.fillWidth: true; model: ["9:16", "16:9", "1:1"] }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.xs
                            Text { text: "FPS"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.label }
                            AppComboBox { id: fpsBox; Layout.fillWidth: true; model: [24, 25, 30, 50, 60]; currentIndex: 2 }
                        }
                    }

                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        AppButton { text: "Create Project"; iconName: "plus"; onClicked: root.createProject() }
                    }
                }
            }
            Item { Layout.preferredHeight: Theme.spacing.sm }
        }
    }
}
