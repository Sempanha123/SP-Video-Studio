import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { property var controller
    RowLayout { anchors.fill:parent; spacing:Theme.spacing.md
        Text { text:(controller.currentBatch.completedItems||0)+" / "+(controller.currentBatch.totalItems||0)+" completed"; color:Theme.colors.textPrimary }
        ProgressBar { Layout.fillWidth:true; value: controller.currentBatch.overallProgress || 0 }
        Text { text:Math.round((controller.currentBatch.overallProgress||0)*100)+"%"; color:Theme.colors.textSecondary }
        Text { visible:!!controller.currentBatch.pauseReason; text:controller.currentBatch.pauseReason==="low_disk_space" ? "Paused — Low Disk Space" : controller.currentBatch.pauseReason; color:Theme.colors.textSecondary }
        Button { text:"Pause"; enabled:controller.currentBatch.status==="running"; onClicked:controller.pauseBatch() }
        Button { text:"Resume"; enabled:controller.currentBatch.status==="paused" || controller.currentBatch.status==="ready"; onClicked:controller.resumeBatch() }
        Button { text:"Cancel"; enabled:controller.currentBatch.status==="running" || controller.currentBatch.status==="paused"; onClicked:controller.cancelBatch(false) }
    }
}
