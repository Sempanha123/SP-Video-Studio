import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    required property var controller
    signal navigateRequested(string mode)
    implicitHeight:180
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            Text { text:"8 · Readiness"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
            Item { Layout.fillWidth:true }
            Text { text:controller.readiness.state || "Not Ready"; color:Theme.colors.textSecondary; font.weight:Font.DemiBold }
        }
        Text { text:(controller.readiness.blocking||[]).join(" · ") || "No blocking issues"; color:Theme.colors.textSecondary; wrapMode:Text.Wrap; Layout.fillWidth:true }
        Text { visible:(controller.readiness.warnings||[]).length>0; text:(controller.readiness.warnings||[]).join(" · "); color:Theme.colors.textMuted; wrapMode:Text.Wrap; Layout.fillWidth:true }
        RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }
            SecondaryButton { text:"Target Subtitles"; onClicked:controller.createSubtitles(false) }
            SecondaryButton { text:"Bilingual"; onClicked:controller.createSubtitles(true) }
            SecondaryButton { text:"Timeline"; onClicked:root.navigateRequested("timeline") }
            AppButton { text:"Export Dubbed Video"; enabled:(controller.readiness.state||"")!=="Not Ready"; onClicked:root.navigateRequested("export") }
        }
    }
}
