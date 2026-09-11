import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property var controller
    property var overview: controller ? controller.overview : ({})
    spacing: Theme.spacing.md

    function hasDiskState(value) {
        var rows = controller ? controller.diskStatus : []
        for (var i = 0; i < rows.length; ++i)
            if (rows[i].state === value) return true
        return false
    }

    AppCard {
        Layout.fillWidth: true
        implicitHeight: 108
        ColumnLayout {
            anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.xs
            Text { text: "Storage Used"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout {
                Layout.fillWidth: true
                Text { text: root.overview.totalOwnedDisplay || "0 B"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.display; font.weight: Theme.type.semibold }
                Item { Layout.fillWidth: true }
                SecondaryButton { text: root.controller && root.controller.calculating ? "Calculating…" : "Recalculate"; enabled: root.controller && !root.controller.calculating; compact: true; onClicked: root.controller.recalculate() }
            }
            Text { text: "Managed application storage only. External referenced media is not counted as owned usage."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }

    InfoBanner {
        Layout.fillWidth: true
        visible: root.hasDiskState("critical") || root.hasDiskState("low")
        variant: root.hasDiskState("critical") ? "warning" : "info"
        text: root.hasDiskState("critical") ? "Storage is almost full. Free space before rendering or other large jobs." : "Disk space is getting low. Consider clearing safe cache files."
    }
}
