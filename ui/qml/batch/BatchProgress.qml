import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { property var controller; implicitHeight: 60
    RowLayout { anchors.fill: parent; spacing: Theme.spacing.md
        ColumnLayout { spacing: 1
            Text { text: (controller.currentBatch.completedItems||0) + " Done"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
            Text { text: (controller.currentBatch.totalItems||0) + " total"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        SoftProgressBar { Layout.fillWidth: true; accessibleName: "Overall batch progress"; value: controller.currentBatch.overallProgress || 0 }
        Text { text: Math.round((controller.currentBatch.overallProgress||0)*100) + "%"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        StatusBadge { visible: !!controller.currentBatch.pauseReason; text: controller.currentBatch.pauseReason === "low_disk_space" ? "Paused · Low disk" : controller.currentBatch.pauseReason; status: "warning" }
        AppButton { text: "Pause"; variant: "quiet"; size: "small"; enabled: controller.currentBatch.status === "running"; onClicked: controller.pauseBatch() }
        AppButton { text: "Resume"; variant: "secondary"; size: "small"; enabled: controller.currentBatch.status === "paused" || controller.currentBatch.status === "ready"; onClicked: controller.resumeBatch() }
        AppButton { text: "Cancel"; variant: "danger"; size: "small"; enabled: controller.currentBatch.status === "running" || controller.currentBatch.status === "paused"; onClicked: controller.cancelBatch(false) }
    }
}
