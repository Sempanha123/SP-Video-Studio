import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"

Item {
    id: root
    property var media: ({})

    ColumnLayout {
        anchors.centerIn: parent
        spacing: Theme.spacing.md
        Icon {
            Layout.alignment: Qt.AlignHCenter
            width: 56
            height: 56
            name: "audio"
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: 360
            text: root.media.name || "Audio"
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.heading
            font.weight: Theme.type.semibold
            elide: Text.ElideMiddle
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: {
                var parts = []
                if (root.media.sampleRate) parts.push(root.media.sampleRate)
                if (root.media.channels) parts.push(root.media.channels)
                if (root.media.duration) parts.push(root.media.duration)
                return parts.join(" · ")
            }
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.bodySmall
        }
    }
}
