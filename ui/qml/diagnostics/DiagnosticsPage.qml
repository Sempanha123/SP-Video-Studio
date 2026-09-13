import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Diagnostics 1.0
import "../theme"
import "../components"

Item {
    id: root
    signal navigateRequested(string page, string context)
    property string tab: "health"

    function currentProjectId() {
        return typeof projectController !== "undefined" ? String(projectController.currentProject.id || "") : ""
    }
    function handleAction(action) {
        if (action === "open_models" || action === "repair_model") root.navigateRequested("models", "")
        else if (action === "open_storage") root.navigateRequested("settings", "Storage")
        else if (action === "choose_ffmpeg") root.navigateRequested("settings", "Advanced")
        else if (action === "open_projects" || action === "locate_media") root.navigateRequested("projects", "")
        else if (action === "rebuild_app_dirs") Diagnostics.rebuildAppDirectories()
        else if (action === "recheck") Diagnostics.runQuick()
    }

    DiagnosticDetails { id: detailsDialog; parent: Overlay.overlay; onCopyRequested: function(value) { Diagnostics.copyText(value) } }
    SupportBundleDialog { id: bundleDialog; parent: Overlay.overlay }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.lg
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "System Health"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { Layout.fillWidth: true; text: "Friendly local diagnostics first; raw technical details stay collapsed until you ask for them."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            AppButton { text: "Run Quick Check"; enabled: !Diagnostics.running; onClicked: Diagnostics.runQuick() }
            SecondaryButton { text: "Run Full Diagnostics"; enabled: !Diagnostics.running; onClicked: Diagnostics.runFull(root.currentProjectId()) }
            SecondaryButton { visible: Diagnostics.running; text: "Cancel"; onClicked: Diagnostics.cancel() }
        }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { text: "Health"; compact: true; onClicked: root.tab = "health" }
            SecondaryButton { text: "Logs"; compact: true; onClicked: root.tab = "logs" }
            SecondaryButton { text: "Diagnose Current Project"; compact: true; enabled: root.currentProjectId().length > 0 && !Diagnostics.running; onClicked: Diagnostics.diagnoseProject(root.currentProjectId()) }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Copy Report"; compact: true; enabled: Diagnostics.results.length > 0; onClicked: Diagnostics.copyShortReport() }
            SecondaryButton { text: "Support Bundle"; compact: true; onClicked: bundleDialog.open() }
        }
        InfoBanner {
            visible: Diagnostics.running
            Layout.fillWidth: true
            text: Diagnostics.mode === "full" ? "Full diagnostics are running in the background. Model inference is not started automatically." : (Diagnostics.mode === "bundle" ? "Creating a local privacy-safe support bundle…" : "Running lightweight diagnostics…")
        }
        LogViewer { visible: root.tab === "logs"; Layout.fillWidth: true; Layout.fillHeight: true }
        ScrollView {
            visible: root.tab === "health"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: Theme.spacing.md
                EmptyState {
                    visible: Diagnostics.results.length === 0 && !Diagnostics.running
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    title: "No diagnostic results yet"
                    description: "Run Quick Check for a lightweight health overview."
                    iconName: "settings"
                    actionText: "Run Quick Check"
                    onActionClicked: Diagnostics.runQuick()
                }
                Repeater {
                    model: Diagnostics.results
                    delegate: DiagnosticCheckCard {
                        required property var modelData
                        Layout.fillWidth: true
                        resultData: modelData
                        onDetailsRequested: function(data) { detailsDialog.resultData = data; detailsDialog.open() }
                        onActionRequested: function(action) { root.handleAction(action) }
                    }
                }
                Item { Layout.preferredHeight: Theme.spacing.md }
            }
        }
    }
}
