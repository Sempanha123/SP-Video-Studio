import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property string actionProjectId: ""
    property string actionProjectTitle: ""
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function projectsModel() {
        return typeof projectController !== "undefined" ? projectController.projects : []
    }
    function openProject(projectId) {
        if (typeof projectController !== "undefined" && projectController.openProject(projectId))
            root.navigateRequested("workspace", "")
    }
    function showRename(projectId, title) {
        actionProjectId = projectId
        actionProjectTitle = title
        renameField.text = title
        renameDialog.open()
        renameField.forceActiveFocus()
    }
    function showDelete(projectId, title) {
        actionProjectId = projectId
        actionProjectTitle = title
        deleteDialog.open()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.xl

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Text { text: "Projects"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Create, reopen and manage your saved video projects."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            AppButton { text: "New Project"; iconName: "plus"; onClicked: root.navigateRequested("create", "news") }
        }

        AppCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.projectsModel().length === 0
            EmptyState {
                anchors.centerIn: parent
                title: "No projects yet"
                description: "Create your first video project and start building."
                iconName: "projects"
                actionText: "Create Project"
                onActionClicked: root.navigateRequested("create", "news")
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.projectsModel().length > 0
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: Theme.spacing.md
                Repeater {
                    model: root.projectsModel()
                    delegate: ProjectCard {
                        required property var modelData
                        Layout.fillWidth: true
                        projectData: modelData
                        onOpenRequested: function(projectId) { root.openProject(projectId) }
                        onRenameRequested: function(projectId, title) { root.showRename(projectId, title) }
                        onDuplicateRequested: function(projectId) {
                            if (typeof projectController !== "undefined") projectController.duplicateProject(projectId)
                        }
                        onDeleteRequested: function(projectId, title) { root.showDelete(projectId, title) }
                    }
                }
                Item { Layout.preferredHeight: Theme.spacing.sm }
            }
        }
    }

    AppDialog {
        id: renameDialog
        width: 440
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        closePolicy: Popup.CloseOnEscape
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Rename Project"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { text: "Change the display name. The project folder and ID will stay the same."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            AppTextField { id: renameField; Layout.fillWidth: true; maximumLength: 120; onAccepted: renameSave.clicked() }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: renameDialog.close() }
                AppButton {
                    id: renameSave
                    text: "Rename"
                    onClicked: {
                        if (renameField.text.trim().length === 0) {
                            root.toastRequested("Project name cannot be empty.", "warning")
                            return
                        }
                        if (typeof projectController !== "undefined" && projectController.renameProject(root.actionProjectId, renameField.text.trim()))
                            renameDialog.close()
                    }
                }
            }
        }
    }

    AppDialog {
        id: deleteDialog
        width: 450
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null
        footer: null
        closePolicy: Popup.CloseOnEscape
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Delete \"" + root.actionProjectTitle + "\"?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: "This will permanently remove the project files and its library record. This action cannot be undone."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }
                AppButton {
                    text: "Delete Project"
                    variant: "danger"
                    iconName: "trash"
                    onClicked: {
                        if (typeof projectController !== "undefined" && projectController.deleteProject(root.actionProjectId))
                            deleteDialog.close()
                    }
                }
            }
        }
    }
}
