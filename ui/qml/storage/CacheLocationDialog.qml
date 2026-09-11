import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

AppDialog {
    id: root
    property var controller
    property string selectedPath: ""
    property bool deleteOldAfterFresh: false
    width: 560
    header: null; footer: null
    FolderDialog { id: folderDialog; title: "Choose Cache Location"; onAccepted: root.selectedPath = selectedFolder.toString() }
    onOpened: { selectedPath = ""; deleteOldAfterFresh = false }
    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text { text: "Cache Location"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: "Cache files are disposable and can be rebuilt. Moving cache is disabled while heavy jobs are active."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        AppTextField { Layout.fillWidth: true; readOnly: true; text: root.selectedPath || (controller ? controller.preferences.cacheRoot : ""); placeholderText: "Choose a folder" }
        SecondaryButton { text: "Choose New Folder"; onClicked: folderDialog.open() }
        Text { text: "Choose how to switch"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
        RowLayout {
            Layout.fillWidth: true
            AppSwitch { checked: root.deleteOldAfterFresh; onToggled: root.deleteOldAfterFresh = checked }
            Text { Layout.fillWidth: true; text: "Delete old cache after Start Fresh"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        }
        RowLayout {
            Layout.fillWidth: true
            AppButton { text: "Move Existing Cache"; enabled: root.selectedPath.length > 0; onClicked: { if (controller.changeCacheLocation(root.selectedPath,"move",true)) root.close() } }
            SecondaryButton { text: "Start Fresh"; enabled: root.selectedPath.length > 0; onClicked: { if (controller.changeCacheLocation(root.selectedPath,"start_fresh",root.deleteOldAfterFresh)) root.close() } }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Cancel"; onClicked: root.close() }
        }
    }
}
