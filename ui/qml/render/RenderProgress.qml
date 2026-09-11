import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    implicitHeight: 150
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Rendering Video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Text { text: root.controller ? root.controller.statusMessage : "Preparing render…"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            Text { text: root.controller ? Math.round(root.controller.progress * 100) + "%" : "0%"; color: Theme.colors.accent; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        }
        ProgressBar { Layout.fillWidth: true; from: 0; to: 1; value: root.controller ? root.controller.progress : 0 }
        RowLayout { Layout.fillWidth: true
            Text { text: root.controller && root.controller.speed > 0 ? "Speed " + root.controller.speed.toFixed(2) + "x" : "Render snapshot remains stable while you keep editing."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            AppButton { text: "Cancel"; compact: true; variant: "danger"; onClicked: if (root.controller) root.controller.cancel() }
        }
    }
}
