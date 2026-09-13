import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property bool indeterminateStage: controller && (controller.stage === "preparing" || controller.stage === "cancelling")
    accessibleName: (controller ? controller.statusMessage : "Preparing export") + (indeterminateStage ? "" : ", " + Math.round((controller ? controller.progress : 0) * 100) + " percent")
    implicitHeight: 180
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Exporting Video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Text { text: root.controller ? root.controller.statusMessage : "Preparing export…"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            }
            Text { text: root.indeterminateStage ? "Working…" : (root.controller ? Math.round(root.controller.progress*100)+"%" : "0%"); color: Theme.colors.accent; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        }
        ProgressBar {
            Layout.fillWidth: true
            from: 0; to: 1
            value: root.controller ? root.controller.progress : 0
            indeterminate: root.indeterminateStage
            Accessible.name: root.controller ? root.controller.statusMessage : "Export progress"
            Accessible.role: Accessible.ProgressBar
        }
        RowLayout { Layout.fillWidth: true
            Text { text: root.controller && root.controller.speed>0 ? "Speed " + root.controller.speed.toFixed(2) + "x" : "Export stays inside this app while it is running."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            AppButton { text: root.controller && root.controller.stage === "cancelling" ? "Cancelling…" : "Cancel Export"; compact: true; variant: "danger"; enabled: !root.controller || root.controller.stage !== "cancelling"; onClicked: if(root.controller) root.controller.cancel() }
        }
    }
}
