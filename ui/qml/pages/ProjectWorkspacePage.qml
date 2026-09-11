import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property string actionProjectId: typeof projectController !== "undefined" ? (projectController.currentProject.id || "") : ""
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function current() {
        return typeof projectController !== "undefined" ? projectController.currentProject : ({})
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: Theme.spacing.xl

            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: "Projects"; iconName: "back"; onClicked: root.navigateRequested("projects", "") }
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Rename"; iconName: "edit"; onClicked: { renameField.text = root.current().title || ""; renameDialog.open(); renameField.forceActiveFocus() } }
                SecondaryButton {
                    text: "Duplicate"; iconName: "copy"
                    onClicked: if (typeof projectController !== "undefined") projectController.duplicateProject(root.current().id)
                }
                AppButton { text: "Delete"; variant: "danger"; iconName: "trash"; onClicked: deleteDialog.open() }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: Theme.spacing.xs
                Text { text: root.current().title || "Project Workspace"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold; Layout.fillWidth: true; elide: Text.ElideRight }
                Text { text: "Project workspace"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width < 850 ? 2 : 4
                columnSpacing: Theme.spacing.md
                rowSpacing: Theme.spacing.md

                Repeater {
                    model: [
                        { label: "Workflow", value: root.current().workflowName || "—" },
                        { label: "Language", value: root.current().languageName || "—" },
                        { label: "Format", value: (root.current().aspectRatio || "—") + " · " + (root.current().fps || 30) + " FPS" },
                        { label: "Status", value: root.current().statusName || "Draft" },
                        { label: "Created", value: root.current().createdDisplay || "—" },
                        { label: "Last Updated", value: root.current().updatedDisplay || "—" }
                    ]
                    delegate: AppCard {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 86
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 3
                            Text { text: modelData.label; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                            Text { Layout.fillWidth: true; text: modelData.value; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                        }
                    }
                }
            }

            AppCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 300
                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - Theme.spacing.xl * 2, 560)
                    spacing: Theme.spacing.md
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: 64; height: 64; radius: 20
                        color: Theme.colors.accentSoft
                        Icon { anchors.centerIn: parent; width: 28; height: 28; name: "video" }
                    }
                    Text { Layout.fillWidth: true; text: "Your project workspace is ready."; horizontalAlignment: Text.AlignHCenter; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                    Text { Layout.fillWidth: true; text: "Media, AI tools and timeline editing will be added in later phases. Your project metadata is already saved safely."; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                }
            }
        }
    }

    AppDialog {
        id: renameDialog
        width: 440
        parent: Overlay.overlay
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Rename Project"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            AppTextField { id: renameField; Layout.fillWidth: true; maximumLength: 120 }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: renameDialog.close() }
                AppButton {
                    text: "Rename"
                    onClicked: {
                        if (renameField.text.trim().length === 0) { root.toastRequested("Project name cannot be empty.", "warning"); return }
                        if (typeof projectController !== "undefined" && projectController.renameProject(root.current().id, renameField.text.trim())) renameDialog.close()
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
        header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { Layout.fillWidth: true; text: "Delete \"" + (root.current().title || "this project") + "\"?"; wrapMode: Text.WordWrap; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: "The project files will be permanently deleted."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }
                AppButton {
                    text: "Delete Project"; variant: "danger"; iconName: "trash"
                    onClicked: {
                        if (typeof projectController !== "undefined" && projectController.deleteProject(root.current().id)) {
                            deleteDialog.close()
                            root.navigateRequested("projects", "")
                        }
                    }
                }
            }
        }
    }
}
