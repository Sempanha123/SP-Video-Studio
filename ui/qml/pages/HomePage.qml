import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
import "../WorkflowData.js" as WorkflowData

Item {
    id: root
    signal navigateRequested(string page, string workflow)

    function accentFor(name) {
        if (name === "news") return Theme.colors.news
        if (name === "story") return Theme.colors.story
        if (name === "translate") return Theme.colors.translate
        if (name === "video") return Theme.colors.video
        if (name === "shorts") return Theme.colors.shorts
        return Theme.colors.batch
    }
    function recentModel() {
        return typeof projectController !== "undefined" ? projectController.recentProjects : []
    }
    function openRecent(projectId) {
        if (typeof projectController !== "undefined" && projectController.openProject(projectId))
            root.navigateRequested("workspace", "")
    }

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
                Text { text: "Create something great"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Choose a workflow to get started. Your recent projects stay close at hand."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }

            SectionHeader { title: "Quick Create"; Layout.fillWidth: true }
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
                        onClicked: root.navigateRequested("create", modelData.key)
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width < 760 ? 1 : 2
                columnSpacing: Theme.spacing.lg
                rowSpacing: Theme.spacing.lg

                AppCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 278
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spacing.lg
                        spacing: Theme.spacing.sm
                        RowLayout {
                            Layout.fillWidth: true
                            SectionHeader { title: "Recent Projects"; Layout.fillWidth: true }
                            SecondaryButton { visible: root.recentModel().length > 0; text: "View All"; compact: true; onClicked: root.navigateRequested("projects", "") }
                        }
                        EmptyState {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: root.recentModel().length === 0
                            title: "No recent projects"
                            description: "Create your first project and it will appear here."
                            iconName: "projects"
                            actionText: "Create Project"
                            onActionClicked: root.navigateRequested("create", "news")
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: root.recentModel().length > 0
                            spacing: Theme.spacing.sm
                            Repeater {
                                model: root.recentModel().slice(0, 3)
                                delegate: RecentProjectCard {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    projectData: modelData
                                    onOpenRequested: function(projectId) { root.openRecent(projectId) }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }

                AppCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 278
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                        SectionHeader { title: "System Readiness"; Layout.fillWidth: true }
                        RowLayout { Layout.fillWidth: true; Text { text: "Project database"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.fillWidth: true }; StatusBadge { text: "Ready"; status: "ready" } }
                        RowLayout { Layout.fillWidth: true; Text { text: "Project storage"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.fillWidth: true }; StatusBadge { text: "Ready"; status: "ready" } }
                        RowLayout { Layout.fillWidth: true; Text { text: "AI models"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.fillWidth: true }; StatusBadge { text: "Not Installed"; status: "not-installed" } }
                        RowLayout { Layout.fillWidth: true; Text { text: "Media engine"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.fillWidth: true }; StatusBadge { text: "Later phase"; status: "offline" } }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            AppCard {
                Layout.fillWidth: true; Layout.preferredHeight: 128
                RowLayout {
                    anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.lg
                    Rectangle { width: 42; height: 42; radius: Theme.radius.large; color: Theme.colors.surfaceHover; Icon { anchors.centerIn: parent; width: 21; height: 21; name: "export" } }
                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Text { text: "Recent Exports"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "Finished videos will be easy to find here once exporting is available."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }
            Item { Layout.preferredHeight: Theme.spacing.xs }
        }
    }
}
