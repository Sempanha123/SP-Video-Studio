import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Dialog {
    id: root
    property var controller
    property bool logoOnly: false
    property string selectedId: ""
    signal mediaChosen(string mediaId)
    modal: true
    width: 620
    height: 520
    title: logoOnly ? "Choose Logo Image" : "Choose Scene Visual"
    standardButtons: Dialog.Cancel

    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        Text { text: root.logoOnly ? "Choose an image from Project Media." : "Choose an image or video from Project Media."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        GridView {
            id: grid
            Layout.fillWidth: true
            Layout.fillHeight: true
            cellWidth: 180
            cellHeight: 154
            clip: true
            model: root.controller ? root.controller.mediaOptions : []
            delegate: AppCard {
                width: 168; height: 142
                interactive: true
                visible: !root.logoOnly || modelData.type === "image"
                onClicked: { root.mediaChosen(modelData.id); root.close() }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: Theme.spacing.sm; spacing: Theme.spacing.xs
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 92; radius: Theme.radius.small; color: Theme.colors.surfaceHover; clip: true
                        Image { anchors.fill: parent; source: modelData.thumbnailUrl || ""; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                    }
                    Text { Layout.fillWidth: true; text: modelData.name || "Media"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    Text { text: (modelData.type || "").toUpperCase(); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                }
            }
        }
        InfoBanner { Layout.fillWidth: true; visible: root.controller && root.controller.mediaOptions.length === 0; text: "Import images or videos in Project Media first."; variant: "info" }
    }
}
