import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    signal toastRequested(string message, string variant)
    property string filterMode: "all"
    property string searchText: ""
    property var pendingModel: ({})
    property string pendingAction: "install"
    property var detailModel: ({})

    function readiness() {
        return typeof readinessController !== "undefined" ? readinessController.readiness : ({})
    }

    function matchesFilter(item) {
        if (!item) return false
        var search = root.searchText.trim().toLowerCase()
        if (search.length > 0) {
            var haystack = ((item.name || "") + " " + (item.description || "") + " " + (item.family || "")).toLowerCase()
            if (haystack.indexOf(search) < 0) return false
        }
        if (root.filterMode === "voice") return item.purpose === "voice"
        if (root.filterMode === "speech") return item.purpose === "speech-to-text"
        if (root.filterMode === "installed") return item.status === "installed"
        return true
    }

    function requestInstall(item, action) {
        pendingModel = item
        pendingAction = action || "install"
        installDialog.open()
    }

    function requestRemove(item) {
        pendingModel = item
        removeDialog.open()
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: root.width
            spacing: Theme.spacing.xl

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: "AI Models"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                    Text { text: "Install, verify and manage local AI models without loading them into memory."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
                }
                StatusBadge { text: "Storage " + (typeof modelController !== "undefined" ? modelController.totalModelStorage : "0 B"); status: "ready" }
                SecondaryButton { text: "Refresh"; iconName: "refresh"; compact: true; enabled: typeof modelController !== "undefined" && !modelController.busy; onClicked: modelController.refresh() }
            }

            AppCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 108
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.lg
                    spacing: Theme.spacing.xl
                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Text { text: "System Compatibility"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "Model recommendations use detected RAM, GPU/CUDA and available storage as guidance."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    ColumnLayout { spacing: 2; Text { text: "RAM"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.readiness().ramTotalDisplay || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
                    ColumnLayout { spacing: 2; Text { text: "GPU"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.readiness().gpuName || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; elide: Text.ElideRight; Layout.maximumWidth: 210 } }
                    ColumnLayout { spacing: 2; Text { text: "CUDA"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; StatusBadge { text: root.readiness().cudaStatusDisplay || "Unknown"; status: root.readiness().cudaStatus || "unknown" } }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing.sm
                AppTextField { Layout.preferredWidth: 280; placeholderText: "Search models"; text: root.searchText; onTextChanged: root.searchText = text }
                AppButton { text: "All"; variant: root.filterMode === "all" ? "primary" : "ghost"; compact: true; onClicked: root.filterMode = "all" }
                AppButton { text: "Voice"; variant: root.filterMode === "voice" ? "primary" : "ghost"; compact: true; onClicked: root.filterMode = "voice" }
                AppButton { text: "Speech-to-Text"; variant: root.filterMode === "speech" ? "primary" : "ghost"; compact: true; onClicked: root.filterMode = "speech" }
                AppButton { text: "Installed"; variant: root.filterMode === "installed" ? "primary" : "ghost"; compact: true; onClicked: root.filterMode = "installed" }
                Item { Layout.fillWidth: true }
                Text { text: typeof modelController !== "undefined" && modelController.activeModelId.length > 0 ? "1 download active" : ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width < 940 ? 1 : 2
                columnSpacing: Theme.spacing.lg
                rowSpacing: Theme.spacing.lg

                Repeater {
                    model: typeof modelController !== "undefined" ? modelController.models : null
                    delegate: ModelCard {
                        required property var modelData
                        Layout.fillWidth: true
                        visible: root.matchesFilter(modelData)
                        dataMap: modelData
                        onInstallRequested: function(data) { root.requestInstall(data, "install") }
                        onCancelRequested: function(modelId) { modelController.cancelDownload(modelId) }
                        onVerifyRequested: function(modelId) { modelController.verify(modelId) }
                        onRepairRequested: function(data) { root.requestInstall(data, "repair") }
                        onRemoveRequested: function(data) { root.requestRemove(data) }
                        onOpenFolderRequested: function(modelId) { modelController.openFolder(modelId) }
                        onRemovePartialRequested: function(modelId) { modelController.removePartial(modelId) }
                        onDetailsRequested: function(data) { root.detailModel = data; detailsDialog.open() }
                    }
                }
            }

            Item { Layout.preferredHeight: Theme.spacing.xs }
        }
    }

    AppDialog {
        id: installDialog
        width: 510
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: (root.pendingAction === "repair" ? "Repair " : "Install ") + (root.pendingModel.name || "AI model") + "?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: root.pendingAction === "repair" ? "Repair performs a safe reinstallation using the official model source. Existing projects and generated files are not removed." : "This downloads the model into MMO Video Studio's managed Models folder. The model will not be loaded or run in this phase."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: Theme.spacing.xl; rowSpacing: Theme.spacing.sm
                Text { text: "Download"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { text: root.pendingModel.downloadSizeDisplay || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Disk"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { text: root.pendingModel.diskSizeDisplay || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Compatibility"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { text: root.pendingModel.compatibilityDisplay || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Source"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                Text { text: root.pendingModel.sourceIdentifier || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: installDialog.close() }
                AppButton {
                    text: root.pendingAction === "repair" ? "Repair" : "Install"
                    onClicked: {
                        var id = root.pendingModel.id || ""
                        var action = root.pendingAction
                        installDialog.close()
                        if (action === "repair") modelController.repair(id)
                        else modelController.install(id)
                    }
                }
            }
        }
    }

    AppDialog {
        id: removeDialog
        width: 500
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Remove " + (root.pendingModel.name || "AI model") + "?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: "This removes the managed local AI model files (about " + (root.pendingModel.diskUsageDisplay || root.pendingModel.diskSizeDisplay || "the installed size") + "). Projects, scripts, media and generated outputs are not deleted."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: removeDialog.close() }; AppButton { text: "Remove"; variant: "danger"; onClicked: { var id = root.pendingModel.id || ""; removeDialog.close(); modelController.remove(id) } } }
        }
    }

    AppDialog {
        id: detailsDialog
        width: 620
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            RowLayout { Layout.fillWidth: true; Text { text: root.detailModel.name || "Model Details"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; Layout.fillWidth: true }; ModelStatusBadge { modelStatus: root.detailModel.status || "not_installed" } }
            Text { Layout.fillWidth: true; text: root.detailModel.description || ""; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: Theme.spacing.xl; rowSpacing: Theme.spacing.sm
                Text { text: "Purpose"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.detailModel.purpose === "voice" ? "Text-to-Speech / Voice" : "Speech-to-Text"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Version"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.detailModel.version || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "License"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.detailModel.license || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Languages"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: (root.detailModel.supportedLanguages || []).join(", "); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Download / Disk"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: (root.detailModel.downloadSizeDisplay || "Unknown") + " / " + (root.detailModel.diskSizeDisplay || "Unknown"); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Source"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: root.detailModel.sourceIdentifier || "Unknown"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                Text { text: "Install path"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { Layout.fillWidth: true; text: root.detailModel.installPath || "Not installed"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WrapAnywhere }
            }
            InfoBanner { visible: (root.detailModel.compatibilityWarnings || []).length > 0; Layout.fillWidth: true; variant: "warning"; text: (root.detailModel.compatibilityWarnings || []).join("  •  ") }
            Text { visible: (root.detailModel.errorMessage || "").length > 0; Layout.fillWidth: true; text: root.detailModel.errorMessage || ""; color: Theme.colors.danger; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; wrapMode: Text.WordWrap }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Close"; onClicked: detailsDialog.close() } }
        }
    }

    Component.onCompleted: if (typeof modelController !== "undefined") modelController.refresh()
}
