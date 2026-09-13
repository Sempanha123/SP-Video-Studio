import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Diagnostics 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    width: Math.min(650, parent ? parent.width - 48 : 650)
    height: Math.min(620, parent ? parent.height - 48 : 620)
    header: null
    footer: null
    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        Text { text: "Create Local Support Bundle"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
        InfoBanner { Layout.fillWidth: true; text: "Nothing is uploaded. Review the privacy boundary before creating the ZIP." }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: Theme.spacing.lg
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Included"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Repeater { model: Diagnostics.bundleReview.included || []; delegate: Text { required property string modelData; Layout.fillWidth: true; text: "• " + modelData; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: "Not included"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Repeater { model: Diagnostics.bundleReview.notIncluded || []; delegate: Text { required property string modelData; Layout.fillWidth: true; text: "• " + modelData; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border }
        Text { visible: Diagnostics.lastBundlePath.length > 0; Layout.fillWidth: true; text: "Created: " + Diagnostics.lastBundlePath; wrapMode: Text.WrapAnywhere; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        ScrollView {
            visible: Diagnostics.lastBundleFiles.length > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            Text { width: parent.width; text: Diagnostics.lastBundleFiles.join("\n"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        Item { visible: Diagnostics.lastBundleFiles.length === 0; Layout.fillHeight: true }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { visible: Diagnostics.lastBundlePath.length > 0; text: "Open Folder"; onClicked: Diagnostics.openBundleFolder() }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Close"; onClicked: root.close() }
            AppButton { text: Diagnostics.running && Diagnostics.mode === "bundle" ? "Creating…" : "Create Bundle"; enabled: !Diagnostics.running; onClicked: Diagnostics.createSupportBundle() }
        }
    }
}
