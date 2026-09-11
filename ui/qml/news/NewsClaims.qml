import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root; property var controller
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true; ColumnLayout { Layout.fillWidth:true; Text { text:"Claims & Evidence"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }; Text { text:"Approve only claims backed by evidence. Conflicts are never resolved automatically."; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }; AppButton { text:"Build Brief"; onClicked:root.controller.createBrief() } }
        ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; Column { width:parent.width; spacing:Theme.spacing.sm; Repeater { model:root.controller?root.controller.claims:[]; NewsClaimRow { width:parent.width; controller:root.controller; claim:modelData } } } }
    }
}
