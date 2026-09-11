import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppDialog {
    id: root
    property var details: ({})
    signal revealRequested(string mediaId)
    signal removeRequested(string mediaId, string name)

    width: 620
    parent: Overlay.overlay
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? Math.max(Theme.spacing.xl, (parent.height - height) / 2) : 0
    header: null
    footer: null
    closePolicy: Popup.CloseOnEscape

    function rows() {
        var source = [
            { label: "Type", value: root.details.type || "" },
            { label: "Status", value: root.details.status || "" },
            { label: "Duration", value: root.details.duration || "" },
            { label: "Resolution", value: root.details.resolution || "" },
            { label: "Frame rate", value: root.details.fps || "" },
            { label: "Video codec", value: root.details.videoCodec || "" },
            { label: "Audio codec", value: root.details.audioCodec || "" },
            { label: "Sample rate", value: root.details.sampleRate || "" },
            { label: "Channels", value: root.details.channels || "" },
            { label: "File size", value: root.details.fileSize || "" },
            { label: "Imported", value: root.details.importedAt || "" },
            { label: "Original source", value: root.details.originalPath || "" },
            { label: "Project copy", value: root.details.projectPath || "" }
        ]
        var output = []
        for (var i = 0; i < source.length; ++i) if (source[i].value !== "") output.push(source[i])
        return output
    }

    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { Layout.fillWidth: true; text: root.details.name || "Media Details"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; elide: Text.ElideMiddle }
                Text { text: "Project media details"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            IconButton { iconName: "open"; tooltip: "Reveal in Folder"; onClicked: root.revealRequested(root.details.id || "") }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: (root.details.thumbnail || "") !== "" ? 180 : 0
            visible: (root.details.thumbnail || "") !== ""
            radius: Theme.radius.medium
            color: Theme.colors.surfaceHover
            clip: true
            Image { anchors.fill: parent; source: root.details.thumbnail || ""; fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(380, detailsColumn.implicitHeight + Theme.spacing.sm)
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: detailsColumn
                width: parent.width
                spacing: 0
                Repeater {
                    model: root.rows()
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(42, rowContent.implicitHeight + Theme.spacing.sm * 2)
                        color: "transparent"
                        border.color: Theme.colors.border
                        border.width: 0
                        RowLayout {
                            id: rowContent
                            anchors.fill: parent
                            spacing: Theme.spacing.lg
                            Text { Layout.preferredWidth: 116; text: modelData.label; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                            Text { Layout.fillWidth: true; text: modelData.value; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WrapAnywhere; maximumLineCount: 3 }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { text: "Reveal in Folder"; iconName: "folder"; onClicked: root.revealRequested(root.details.id || "") }
            Item { Layout.fillWidth: true }
            AppButton { text: "Remove"; variant: "danger"; iconName: "trash"; onClicked: root.removeRequested(root.details.id || "", root.details.name || "this media") }
            SecondaryButton { text: "Close"; onClicked: root.close() }
        }
    }
}
