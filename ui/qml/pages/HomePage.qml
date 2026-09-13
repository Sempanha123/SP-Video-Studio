import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"
import "../WorkflowData.js" as WorkflowData

Item {
    id: root
    signal navigateRequested(string page, string workflow)
    signal gettingStartedRequested()
    signal quickGuideRequested()

    function accentFor(name) {
        if (name === "news") return Theme.colors.news
        if (name === "story") return Theme.colors.story
        if (name === "translate") return Theme.colors.translate
        if (name === "video") return Theme.colors.video
        if (name === "shorts") return Theme.colors.shorts
        return Theme.colors.batch
    }
    function recentModel() { return typeof projectController !== "undefined" ? projectController.recentProjects : [] }
    function readiness() { return typeof readinessController !== "undefined" ? readinessController.readiness : ({}) }
    function primaryDisk() {
        var disks = root.readiness().disks || []
        for (var i = 0; i < disks.length; ++i) if (disks[i].name === "Projects") return disks[i]
        return disks.length > 0 ? disks[0] : ({ freeDisplay: "Unknown", status: "unknown" })
    }
    function openRecent(projectId) {
        if (typeof projectController !== "undefined" && projectController.openProject(projectId)) root.navigateRequested("workspace", "")
    }

    ScrollView {
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: Theme.spacing.xl
            ColumnLayout {
                Layout.fillWidth: true; spacing: Theme.spacing.xs
                Text { text: "Create something great"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Choose a workflow to get started. Your recent projects stay close at hand."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }

            AppCard {
                visible: root.recentModel().length === 0
                Layout.fillWidth: true; implicitHeight: 116
                RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.lg
                    Rectangle { width: 44; height: 44; radius: Theme.radius.large; color: Theme.colors.accentSoft; Icon { anchors.centerIn: parent; width: 22; height: 22; name: "spark" } }
                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Text { text: "Create your first video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { Layout.fillWidth: true; text: "Start blank, use a template, or reopen the short Getting Started setup."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    }
                    SecondaryButton { text: "Getting Started"; onClicked: root.gettingStartedRequested() }
                    SecondaryButton { text: "Start from Template"; onClicked: root.navigateRequested("templates", "") }
                    AppButton { text: "New Video"; onClicked: root.navigateRequested("create", "video") }
                }
            }

            RowLayout {
                visible: root.recentModel().length > 0
                Layout.fillWidth: true
                AppButton { text: "Continue Editing"; onClicked: root.openRecent(String(root.recentModel()[0].id || "")) }
                SecondaryButton { text: "Templates"; onClicked: root.navigateRequested("templates", "") }
                SecondaryButton { text: "Getting Started"; onClicked: root.gettingStartedRequested() }
                SecondaryButton { text: "Quick Guide"; onClicked: root.quickGuideRequested() }
                Item { Layout.fillWidth: true }
            }

            AppCard {
                visible: (Onboarding.status === "completed" || Onboarding.status === "skipped") && Onboarding.shouldShowTip("home_asset_tip")
                Layout.fillWidth: true; implicitHeight: 76
                RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.md
                    Icon { width: 20; height: 20; name: "assets" }
                    Text { Layout.fillWidth: true; text: "Tip: Project Media is for this project; Asset Library keeps reusable B-roll, music, logos and presenter clips available across projects."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    SecondaryButton { text: "Got it"; compact: true; onClicked: Onboarding.dismissTip("home_asset_tip") }
                }
            }

            SectionHeader { title: "Quick Create"; Layout.fillWidth: true }
            GridLayout {
                Layout.fillWidth: true; columns: width < 840 ? 2 : 3; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                Repeater {
                    model: WorkflowData.modes
                    delegate: CreateModeCard {
                        required property var modelData
                        Layout.fillWidth: true; Layout.minimumWidth: 210
                        title: modelData.title; description: modelData.description; iconName: modelData.icon; mode: modelData.key; accentColor: root.accentFor(modelData.accent)
                        onClicked: root.navigateRequested("create", modelData.key)
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true; columns: width < 760 ? 1 : 2; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                AppCard {
                    Layout.fillWidth: true; Layout.preferredHeight: 278
                    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                        RowLayout { Layout.fillWidth: true; SectionHeader { title: "Recent Projects"; Layout.fillWidth: true }; SecondaryButton { visible: root.recentModel().length > 0; text: "View All"; compact: true; onClicked: root.navigateRequested("projects", "") } }
                        EmptyState { Layout.fillWidth: true; Layout.fillHeight: true; visible: root.recentModel().length === 0; title: "No recent projects"; description: "Create your first project and it will appear here."; iconName: "projects"; actionText: "Create Project"; onActionClicked: root.navigateRequested("create", "video") }
                        ColumnLayout { Layout.fillWidth: true; Layout.fillHeight: true; visible: root.recentModel().length > 0; spacing: Theme.spacing.sm
                            Repeater { model: root.recentModel().slice(0, 3); delegate: RecentProjectCard { required property var modelData; Layout.fillWidth: true; projectData: modelData; onOpenRequested: function(projectId) { root.openRecent(projectId) } } }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }
                AppCard {
                    Layout.fillWidth: true; Layout.preferredHeight: 278
                    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                        RowLayout { Layout.fillWidth: true; SectionHeader { title: "System Readiness"; Layout.fillWidth: true }; StatusBadge { text: readinessController.checking ? "Checking" : (root.readiness().overallDisplay || "Not checked"); status: readinessController.checking ? "checking" : (root.readiness().overallStatus || "unknown") } }
                        RowLayout { Layout.fillWidth: true; Text { text: "GPU"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Layout.fillWidth: true }; Text { text: root.readiness().gpuName || "Detection unavailable"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; elide: Text.ElideRight; Layout.maximumWidth: 190 } }
                        RowLayout { Layout.fillWidth: true; Text { text: "CUDA"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Layout.fillWidth: true }; StatusBadge { text: root.readiness().cudaStatusDisplay || "Unknown"; status: root.readiness().cudaStatus || "unknown" } }
                        RowLayout { Layout.fillWidth: true; Text { text: "FFmpeg"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Layout.fillWidth: true }; StatusBadge { text: root.readiness().ffmpegAvailable ? "Ready" : "Missing"; status: root.readiness().ffmpegAvailable ? "ready" : "setup-required" } }
                        RowLayout { Layout.fillWidth: true; Text { text: "Disk"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Layout.fillWidth: true }; Text { text: root.primaryDisk().freeDisplay + " free"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
                        RowLayout { Layout.fillWidth: true; Text { text: "AI models"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Layout.fillWidth: true }; StatusBadge { text: (root.readiness().voxcpmStatus === "repair-required" || root.readiness().whisperStatus === "repair-required") ? "Needs Repair" : ((root.readiness().voxcpmStatus === "installed" && root.readiness().whisperStatus === "installed") ? "Installed" : ((root.readiness().voxcpmStatus === "installed" || root.readiness().whisperStatus === "installed") ? "Partial" : "Not Installed")); status: (root.readiness().voxcpmStatus === "repair-required" || root.readiness().whisperStatus === "repair-required") ? "repair-required" : ((root.readiness().voxcpmStatus === "installed" && root.readiness().whisperStatus === "installed") ? "installed" : "not-installed") } }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; SecondaryButton { text: "View Details"; compact: true; onClicked: root.navigateRequested("settings", "Performance") }; Item { Layout.fillWidth: true }; SecondaryButton { text: "Recheck"; compact: true; enabled: !readinessController.checking; onClicked: readinessController.recheck() } }
                    }
                }
            }

            AppCard {
                Layout.fillWidth: true; Layout.preferredHeight: 112
                RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.lg
                    Rectangle { width: 42; height: 42; radius: Theme.radius.large; color: Theme.colors.surfaceHover; Icon { anchors.centerIn: parent; width: 21; height: 21; name: "template" } }
                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Text { text: "Templates"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "Templates create reusable structure and styles. Your project becomes independent after applying one."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    SecondaryButton { text: "Browse Templates"; onClicked: root.navigateRequested("templates", "") }
                }
            }
            Item { Layout.preferredHeight: Theme.spacing.xs }
        }
    }
}
