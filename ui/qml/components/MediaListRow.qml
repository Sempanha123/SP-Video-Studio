import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    id: root
    property string mediaId: ""
    property string mediaName: "Untitled media"
    property string mediaType: "video"
    property string typeName: "Video"
    property string thumbnail: ""
    property string duration: ""
    property string resolution: ""
    property string fileSize: ""
    property string mediaStatus: "ready"
    property string statusName: "Ready"
    property bool isSelected: false

    signal activated(string mediaId)
    signal detailsRequested(string mediaId)
    signal revealRequested(string mediaId)
    signal removeRequested(string mediaId, string name)

    height: 68
    radius: Theme.radius.medium
    color: root.isSelected ? Theme.colors.accentSoft : (hover.hovered ? Theme.colors.surfaceHover : "transparent")
    border.width: root.isSelected ? 1 : 0
    border.color: root.isSelected ? Theme.colors.accent : "transparent"

    HoverHandler { id: hover }
    TapHandler { acceptedButtons: Qt.LeftButton; onTapped: root.activated(root.mediaId) }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: actionsMenu.popup() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.sm
        anchors.rightMargin: Theme.spacing.sm
        spacing: Theme.spacing.md

        Rectangle {
            Layout.preferredWidth: 74
            Layout.preferredHeight: 50
            radius: Theme.radius.small
            color: Theme.colors.surfaceHover
            clip: true
            Image { anchors.fill: parent; source: root.thumbnail; visible: root.thumbnail !== ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; smooth: true }
            Icon { anchors.centerIn: parent; width: 22; height: 22; visible: root.thumbnail === ""; name: root.mediaType === "audio" ? "audio" : (root.mediaType === "image" ? "image" : "video") }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text { Layout.fillWidth: true; text: root.mediaName; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideMiddle }
            Text { text: root.typeName; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        Text { Layout.preferredWidth: 86; text: root.duration || "—"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        Text { Layout.preferredWidth: 122; text: root.resolution || "—"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        Text { Layout.preferredWidth: 88; text: root.fileSize; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        StatusBadge { text: root.statusName; status: root.mediaStatus }
        IconButton { iconName: "more"; tooltip: "Media actions"; onClicked: actionsMenu.popup() }
    }

    Menu {
        id: actionsMenu
        width: 188
        background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.surfaceRaised; border.color: Theme.colors.border; border.width: 1 }
        MenuItem {
            id: detailsAction
            text: "View Details"
            contentItem: Text { text: detailsAction.text; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: detailsAction.highlighted ? Theme.colors.surfaceHover : "transparent"; radius: Theme.radius.small }
            onTriggered: root.detailsRequested(root.mediaId)
        }
        MenuItem {
            id: revealAction
            text: "Reveal in Folder"
            contentItem: Text { text: revealAction.text; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: revealAction.highlighted ? Theme.colors.surfaceHover : "transparent"; radius: Theme.radius.small }
            onTriggered: root.revealRequested(root.mediaId)
        }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: Theme.colors.border } }
        MenuItem {
            id: removeAction
            text: root.mediaStatus === "missing" ? "Remove Reference" : "Remove from Project"
            contentItem: Text { text: removeAction.text; color: Theme.colors.danger; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: removeAction.highlighted ? Theme.colors.dangerSoft : "transparent"; radius: Theme.radius.small }
            onTriggered: root.removeRequested(root.mediaId, root.mediaName)
        }
    }
}
