import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var playbackController
    property string aspectRatio: "16:9"
    property var scene: controller ? controller.scene : ({})
    property var overlays: controller ? controller.overlays : []

    color: "#11141B"

    function canvasRatio() {
        if (aspectRatio === "9:16") return 9/16
        if (aspectRatio === "1:1") return 1
        return 16/9
    }

    Item {
        id: viewport
        anchors.centerIn: parent
        width: Math.min(parent.width - Theme.spacing.xl*2, (parent.height - 96) * root.canvasRatio())
        height: width / root.canvasRatio()

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius.medium
            color: root.scene.backgroundEnabled ? (root.scene.backgroundColor || "#10131A") : "#0B0D12"
            clip: true

            Image {
                anchors.fill: parent
                source: root.scene.thumbnailUrl || root.scene.mediaUrl || ""
                fillMode: root.scene.fitMode === "fit" ? Image.PreserveAspectFit : (root.scene.fitMode === "stretch" ? Image.Stretch : Image.PreserveAspectCrop)
                visible: (root.scene.primaryMediaId || "") !== ""
                asynchronous: true
            }

            Rectangle {
                anchors.fill: parent
                visible: (root.scene.primaryMediaId || "") === "" && !root.scene.backgroundEnabled
                color: "transparent"
                border.color: Theme.colors.border
                border.width: 1
                Text { anchors.centerIn: parent; text: "Add a visual\nChoose Image or Video"; horizontalAlignment: Text.AlignHCenter; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }

            Repeater {
                model: root.overlays || []
                delegate: Item {
                    x: (modelData.x || 0) * parent.width
                    y: (modelData.y || 0) * parent.height
                    width: Math.max(1, (modelData.width || .2) * parent.width)
                    height: Math.max(1, (modelData.height || .1) * parent.height)
                    opacity: modelData.opacity === undefined ? 1 : modelData.opacity
                    rotation: modelData.rotation || 0
                    visible: modelData.visible !== false
                    Image {
                        anchors.fill: parent
                        visible: modelData.type === "logo"
                        source: modelData.assetUrl || ""
                        fillMode: Image.PreserveAspectFit
                    }
                    Rectangle {
                        anchors.fill: parent
                        visible: modelData.type === "lower_third"
                        radius: 5
                        color: "#AA10151F"
                    }
                    Column {
                        anchors.centerIn: parent
                        width: parent.width
                        visible: modelData.type !== "logo"
                        spacing: 2
                        Text {
                            width: parent.width
                            text: modelData.text || ""
                            color: modelData.style && modelData.style.color ? modelData.style.color : "white"
                            font.pixelSize: Math.max(12, Math.min(34, (modelData.style && modelData.style.fontSize ? modelData.style.fontSize : 42) * viewport.height / 1080))
                            font.bold: modelData.type === "headline" || modelData.type === "lower_third"
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            width: parent.width
                            visible: (modelData.secondaryText || "") !== ""
                            text: modelData.secondaryText || ""
                            color: "#DDE4EE"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Rectangle { visible: safeGuide.checked; anchors.fill: parent; anchors.margins: Math.min(parent.width,parent.height)*.07; color: "transparent"; border.color: "#55FFFFFF"; border.width: 1; radius: 2 }
        }
    }

    RowLayout {
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm
        AppButton { text: "Play Scene"; compact: true; iconName: "play"; enabled: !!root.controller && (root.scene.primaryMediaId || "") !== ""; onClicked: root.controller.playScene(true) }
        SecondaryButton { text: "Play Narration"; compact: true; visible: (root.scene.narrationAudioId || "") !== ""; onClicked: if (root.controller) root.controller.playNarration() }
        CheckBox { id: safeGuide; text: "Safe area"; checked: false }
        Item { Layout.fillWidth: true }
        StatusBadge { text: (root.scene.status || "incomplete").replace("_"," "); status: root.scene.status || "incomplete" }
    }
}
