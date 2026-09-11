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
                Text { text: "Choose a workflow to get started. You can keep things simple or move into the advanced studio later."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; Layout.fillWidth: true }
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
                    Layout.fillWidth: true; Layout.preferredHeight: 190
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                        SectionHeader { title: "Recent Projects"; Layout.fillWidth: true }
                        Item { Layout.fillHeight: true }
                        EmptyState { Layout.fillWidth: true; title: "No recent projects"; description: "Your latest work will appear here."; iconName: "projects" }
                        Item { Layout.fillHeight: true }
                    }
                }
                AppCard {
                    Layout.fillWidth: true; Layout.preferredHeight: 190
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                        SectionHeader { title: "System Readiness"; Layout.fillWidth: true }
                        RowLayout { Layout.fillWidth: true; Text { text: "Application shell"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; Layout.fillWidth: true }; StatusBadge { text: "Ready"; status: "ready" } }
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
