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
    implicitHeight: 122
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.sm
        spacing: Theme.spacing.xs
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: bus.name || "Bus"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
            AppButton { text: "M"; compact: true; variant: bus.muted ? "primary" : "secondary"; onClicked: if (root.controller) root.controller.setBusMuted(root.bus.id, !root.bus.muted) }
        }
        Text { text: (bus.role || "general").replaceAll("_", " "); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Slider { Layout.fillWidth: true; from: -60; to: 12; stepSize: .5; value: Number(bus.gainDb || 0); onPressedChanged: if (!pressed && root.controller) root.controller.setBusGain(root.bus.id, value) }
        Text { Layout.alignment: Qt.AlignRight; text: Number(bus.gainDb || 0).toFixed(1) + " dB"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
}
