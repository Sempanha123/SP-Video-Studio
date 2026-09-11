import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property var dataMap: ({})
    signal installRequested(var data)
    signal cancelRequested(string modelId)
    signal verifyRequested(string modelId)
    signal repairRequested(var data)
    signal removeRequested(var data)
    signal openFolderRequested(string modelId)
    signal detailsRequested(var data)
    signal removePartialRequested(string modelId)

    Layout.fillWidth: true
    Layout.preferredHeight: dataMap.status === "downloading" || dataMap.status === "verifying" ? 300 : 248

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            Rectangle {
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                radius: Theme.radius.medium
                color: dataMap.purpose === "voice" ? Theme.colors.accentSoft : Theme.colors.surfaceHover
                Icon {
                    anchors.centerIn: parent
                    width: 19; height: 19
                    name: dataMap.purpose === "voice" ? "mic" : "wave"
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: dataMap.name || "AI Model"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                    StatusBadge { visible: dataMap.recommended === true; text: "Recommended"; status: "ready" }
                    Item { Layout.fillWidth: true }
                }
                Text {
                    text: dataMap.purpose === "voice" ? "Text-to-Speech / Voice" : "Speech-to-Text"
                    color: Theme.colors.textSecondary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.caption
                }
            }
            ModelStatusBadge { modelStatus: dataMap.status || "not_installed" }
        }

        Text {
            Layout.fillWidth: true
            text: dataMap.description || ""
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            CompatibilityBadge { compatibility: dataMap.compatibility || "unknown" }
            Text { text: dataMap.downloadSizeDisplay || "Unknown"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: "•"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: dataMap.license || "Unknown license"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
        }

        ModelDownloadProgress {
            visible: dataMap.status === "downloading" || dataMap.status === "verifying"
            Layout.fillWidth: true
            progress: dataMap.progress || 0
            downloadedText: dataMap.downloadedDisplay || "0 B"
            totalText: dataMap.totalDisplay || dataMap.downloadSizeDisplay || ""
            speedBytes: dataMap.downloadSpeed || 0
            currentFile: dataMap.currentFile || ""
        }

        Text {
            visible: (dataMap.status === "failed" || dataMap.status === "repair_required" || dataMap.status === "paused") && (dataMap.errorMessage || "").length > 0
            Layout.fillWidth: true
            text: dataMap.errorMessage || ""
            color: dataMap.status === "failed" ? Theme.colors.danger : Theme.colors.warning
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            AppButton { text: "Details"; variant: "ghost"; compact: true; onClicked: root.detailsRequested(root.dataMap) }
            Item { Layout.fillWidth: true }
            AppButton {
                visible: dataMap.status === "not_installed" || dataMap.status === "failed" || dataMap.status === "paused"
                text: dataMap.status === "paused" ? "Resume" : (dataMap.status === "failed" ? "Retry" : "Install")
                compact: true
                onClicked: root.installRequested(root.dataMap)
            }
            SecondaryButton {
                visible: dataMap.status === "paused"
                text: "Delete Partial"
                compact: true
                onClicked: root.removePartialRequested(dataMap.id || "")
            }
            AppButton {
                visible: dataMap.status === "downloading" || dataMap.status === "verifying"
                text: "Cancel"
                variant: "secondary"
                compact: true
                onClicked: root.cancelRequested(dataMap.id || "")
            }
            SecondaryButton {
                visible: dataMap.status === "installed"
                text: "Verify"
                compact: true
                onClicked: root.verifyRequested(dataMap.id || "")
            }
            SecondaryButton {
                visible: dataMap.status === "installed"
                text: "Open Folder"
                compact: true
                onClicked: root.openFolderRequested(dataMap.id || "")
            }
            AppButton {
                visible: dataMap.status === "repair_required"
                text: "Repair"
                compact: true
                onClicked: root.repairRequested(root.dataMap)
            }
            AppButton {
                visible: dataMap.status === "installed" || dataMap.status === "repair_required"
                text: "Remove"
                variant: "ghost"
                compact: true
                enabled: (dataMap.inUseCount || 0) === 0
                onClicked: root.removeRequested(root.dataMap)
            }
        }
    }
}
