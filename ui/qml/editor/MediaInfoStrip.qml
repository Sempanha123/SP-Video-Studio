import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

RowLayout {
    id: root
    property var media: ({})
    spacing: Theme.spacing.sm

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 1
        Text {
            Layout.fillWidth: true
            text: root.media.name || ""
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.body
            font.weight: Theme.type.semibold
            elide: Text.ElideMiddle
        }
        Text {
            Layout.fillWidth: true
            text: {
                var parts = []
                if (root.media.type === "video") {
                    if (root.media.resolution) parts.push(root.media.resolution)
                    if (root.media.fps) parts.push(root.media.fps)
                    if (root.media.duration) parts.push(root.media.duration)
                } else if (root.media.type === "image") {
                    if (root.media.resolution) parts.push(root.media.resolution)
                } else if (root.media.type === "audio") {
                    if (root.media.sampleRate) parts.push(root.media.sampleRate)
                    if (root.media.channels) parts.push(root.media.channels)
                    if (root.media.duration) parts.push(root.media.duration)
                }
                return parts.join(" · ")
            }
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            elide: Text.ElideRight
        }
    }
}
