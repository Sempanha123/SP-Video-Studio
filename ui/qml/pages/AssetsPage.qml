import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function currentProject() {
        return typeof projectController !== "undefined" ? projectController.currentProject : ({})
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.lg

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text { text: "Asset Library"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            Text { text: "Media is organized inside each project so projects stay portable and originals stay safe."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }

        AppCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            EmptyState {
                anchors.centerIn: parent
                iconName: root.currentProject().id ? "assets" : "projects"
                title: root.currentProject().id ? "Open the current project media" : "Open a project first"
                description: root.currentProject().id ? "Import, search, filter and manage media from the Media workspace for \"" + (root.currentProject().title || "your project") + "\"." : "Choose a project to access its videos, audio and images."
                actionText: root.currentProject().id ? "Open Project Media" : "View Projects"
                onActionClicked: root.navigateRequested(root.currentProject().id ? "workspace" : "projects", "")
            }
        }
    }
}
