import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    property var controller: null
    width: 560
    parent: Overlay.overlay
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    header: null
    footer: null

    property var selectedSource: sourceCombo.currentIndex >= 0 && controller && controller.sources.length > sourceCombo.currentIndex ? controller.sources[sourceCombo.currentIndex] : ({})

    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text { text: "New Translation"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: "Translate a project transcript or script, or use Manual Translation if the local model is not installed."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        GridLayout {
            Layout.fillWidth: true; columns: 2; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.md
            Text { text: "Source"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: sourceCombo; Layout.fillWidth: true; model: root.controller ? root.controller.sources : []; textRole: "name" }
            Text { text: "Target"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: targetCombo; Layout.fillWidth: true; model: ["Khmer", "English"]; currentIndex: root.selectedSource.language === "km" ? 1 : 0 }
            Text { text: "Provider"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: providerCombo; Layout.fillWidth: true; model: root.controller ? root.controller.providers : []; textRole: "name" }
            Text { text: "Device"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: deviceCombo; Layout.fillWidth: true; model: ["Auto", "CPU", "CUDA"] }
            Text { text: "Keep Terms"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppTextField { id: keepTerms; Layout.fillWidth: true; placeholderText: "OpenAI, VoxCPM2, product names…" }
        }
        InfoBanner { Layout.fillWidth: true; variant: "warning"; text: "Review translations before publishing, especially names, numbers and quotes." }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Cancel"; onClicked: root.close() }
            AppButton {
                text: "Translate"
                enabled: root.controller && sourceCombo.currentIndex >= 0
                onClicked: {
                    var source = root.selectedSource
                    var targets = ["km", "en"]
                    var providers = ["local-marian", "manual"]
                    var devices = ["auto", "cpu", "cuda"]
                    if (root.controller.createTranslation(source.type || "", source.id || "", targets[targetCombo.currentIndex], providers[providerCombo.currentIndex], devices[deviceCombo.currentIndex], keepTerms.text)) root.close()
                }
            }
        }
    }
}
