import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    property var bus: ({})
    property var controller
    implicitWidth: 154
    implicitHeight: Math.max(122, Math.round(122 * Theme.textScale))
    accessibleName: (bus.name || "Bus") + ". Gain " + Number(bus.gainDb || 0).toFixed(1) + " decibels" + (bus.muted ? ". Muted" : "")
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.sm
        spacing: Theme.spacing.xs
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: bus.name || "Bus"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
            AppButton { text: "Mute"; compact: true; accessibleName: "Mute " + (bus.name || "bus"); variant: bus.muted ? "primary" : "secondary"; onClicked: if (root.controller) root.controller.setBusMuted(root.bus.id, !root.bus.muted) }
        }
        Text { text: (bus.role || "general").replaceAll("_", " "); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Slider {
            id: busGain
            Layout.fillWidth: true
            from: -60; to: 12; stepSize: .5; value: Number(bus.gainDb || 0)
            Accessible.name: (bus.name || "Bus") + " gain, " + Number(value).toFixed(1) + " decibels"
            Accessible.role: Accessible.Slider
            property bool initialized: false
            Component.onCompleted: initialized = true
            onValueChanged: if (initialized && activeFocus && !pressed && root.controller) root.controller.setBusGain(root.bus.id, value)
            onPressedChanged: if (!pressed && root.controller) root.controller.setBusGain(root.bus.id, value)
        }
        Text { Layout.alignment: Qt.AlignRight; text: Number(bus.gainDb || 0).toFixed(1) + " dB"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
}
