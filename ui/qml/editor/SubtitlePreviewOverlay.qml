import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

Item {
    id: root
    property var controller
    property var styleData: controller ? controller.style : ({})
    property var cue: controller ? controller.activeCue : ({})
    property bool safeAreaVisible: true
    property string aspectRatio: "16:9"

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.safeAreaVisible ? Theme.colors.border : "transparent"
        border.width: root.safeAreaVisible ? 1 : 0
        anchors.margins: root.safeAreaVisible ? Math.max(12, parent.width * 0.06) : 0
        opacity: 0.55
    }

    Column {
        id: captions
        width: Math.min(parent.width * 0.84, 900)
        anchors.horizontalCenter: parent.horizontalCenter
        y: {
            var pos = root.styleData.vertical_position || "bottom"
            if (pos === "top") return parent.height * 0.10
            if (pos === "middle") return (parent.height - height) / 2
            return parent.height - height - Math.max(24, parent.height * (root.styleData.vertical_margin || 0.08))
        }
        spacing: 4
        visible: (root.cue.text || "").length > 0

        Rectangle {
            anchors.fill: primaryText
            anchors.margins: -8
            radius: 6
            color: root.styleData.background_enabled ? (root.styleData.background_color || "#000000") : "transparent"
            opacity: root.styleData.background_enabled ? (root.styleData.background_opacity || 0.5) : 0
            z: -1
        }

        Text {
            id: primaryText
            width: parent.width
            horizontalAlignment: root.styleData.alignment === "left" ? Text.AlignLeft : root.styleData.alignment === "right" ? Text.AlignRight : Text.AlignHCenter
            text: root.cue.text || ""
            color: root.styleData.text_color || "#FFFFFF"
            font.family: root.styleData.font_family || Theme.type.family
            font.pixelSize: Math.max(18, Math.min(54, parent.parent.height * 0.055))
            font.weight: (root.styleData.font_weight || 600) >= 700 ? Font.Bold : Font.DemiBold
            wrapMode: Text.Wrap
            style: Text.Outline
            styleColor: root.styleData.outline_color || "#000000"
        }

        Text {
            width: parent.width
            visible: (root.cue.secondaryText || "").length > 0
            horizontalAlignment: primaryText.horizontalAlignment
            text: root.cue.secondaryText || ""
            color: root.styleData.secondary_text_color || "#E5E7EB"
            font.family: root.styleData.font_family || Theme.type.family
            font.pixelSize: primaryText.font.pixelSize * (root.styleData.secondary_scale || 0.82)
            font.weight: Font.DemiBold
            wrapMode: Text.Wrap
            style: Text.Outline
            styleColor: root.styleData.outline_color || "#000000"
        }

        Rectangle {
            visible: (root.cue.activeWord || "").length > 0 && !!root.styleData.metadata && !!root.styleData.metadata.word_highlight
            anchors.horizontalCenter: parent.horizontalCenter
            width: activeWordLabel.implicitWidth + 16
            height: activeWordLabel.implicitHeight + 8
            radius: 6
            color: root.styleData.highlight_color || "#FDE047"
            Text {
                id: activeWordLabel
                anchors.centerIn: parent
                text: root.cue.activeWord || ""
                color: root.styleData.highlight_text_color || "#111827"
                font.family: root.styleData.font_family || Theme.type.family
                font.pixelSize: Math.max(16, primaryText.font.pixelSize * 0.75)
                font.weight: Font.Bold
            }
        }
    }
}
