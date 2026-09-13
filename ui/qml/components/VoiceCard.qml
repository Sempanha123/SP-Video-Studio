import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string voiceId: ""
    property string voiceName: "Voice"
    property string voiceType: "preset"
    property string category: "Professional"
    property string languageName: "English"
    property var styleTags: []
    property string engineName: "VoxCPM2"
    property bool favorite: false
    property bool recommended: false
    property bool isSelected: false
    signal selectRequested(string voiceId)
    signal previewRequested(string voiceId)
    signal favoriteRequested(string voiceId)

    selected: isSelected
    accessibleName: root.voiceName + ". " + root.languageName + ". " + root.category + ". " + (root.recommended ? "Recommended. " : "") + (root.voiceType === "preset" ? "Preset voice" : "Custom voice")
    implicitHeight: Math.max(176, Math.round(176 * Theme.textScale))

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            Rectangle {
                Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19
                color: Theme.colors.accentSoft
                Icon { anchors.centerIn: parent; width: 18; height: 18; name: "mic" }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 1
                Text {
                    id: voiceNameLabel
                    Layout.fillWidth: true
                    text: root.voiceName
                    elide: Text.ElideRight
                    color: Theme.colors.textPrimary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.heading
                    font.weight: Theme.type.semibold
                    ToolTip.visible: voiceNameHover.hovered && voiceNameLabel.truncated
                    ToolTip.text: root.voiceName
                    ToolTip.delay: Theme.tooltipDelay
                    HoverHandler { id: voiceNameHover }
                }
                Text { Layout.fillWidth: true; text: root.category + "  •  " + root.languageName; elide: Text.ElideRight; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            StatusBadge { visible: root.recommended; text: "Recommended"; status: "ready" }
            IconButton { iconName: root.favorite ? "heart-filled" : "heart"; accessibleName: root.favorite ? "Remove voice from favorites" : "Add voice to favorites"; tooltip: root.favorite ? "Remove favorite" : "Favorite"; onClicked: root.favoriteRequested(root.voiceId) }
        }

        Text {
            Layout.fillWidth: true
            text: root.styleTags && root.styleTags.length ? root.styleTags.slice(0, 3).join("  •  ") : root.engineName
            elide: Text.ElideRight
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            SecondaryButton { text: root.isSelected ? "Selected" : "Select"; compact: true; enabled: !root.isSelected; onClicked: root.selectRequested(root.voiceId) }
            AppButton { text: "Preview"; accessibleName: "Preview " + root.voiceName; iconName: "play"; compact: true; variant: "secondary"; onClicked: { root.selectRequested(root.voiceId); root.previewRequested(root.voiceId) } }
            Item { Layout.fillWidth: true }
            Text { text: root.voiceType === "preset" ? "Preset" : (root.voiceType === "reference" ? "Reference" : "Designed"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 10 }
        }
    }
}
