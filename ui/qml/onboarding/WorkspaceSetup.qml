import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    id: root
    title: "Projects folder"
    description: "New projects will be saved here. Changing this later affects future projects only; existing projects are not moved."
    FolderDialog { id: folderDialog; title: "Choose Projects Folder"; onAccepted: Onboarding.setProjectFolder(selectedFolder.toString()) }
    AppCard {
        Layout.fillWidth: true; implicitHeight: 112
        ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.sm
            Text { text: "Projects Folder"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
            RowLayout { Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: Onboarding.projectFolder; elide: Text.ElideMiddle; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; Accessible.name: "Projects folder " + text }
                SecondaryButton { text: "Change"; accessibleName: "Change projects folder"; onClicked: folderDialog.open() }
            }
        }
    }
    InfoBanner { Layout.fillWidth: true; text: "Only the Projects folder is configured here. Cache and model storage keep their existing safe defaults." }
}
