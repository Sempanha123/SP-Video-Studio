import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id:root; property var controller; signal navigateRequested(string mode)
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.lg
        Text { text:"Source-grounded Script"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        InfoBanner { Layout.fillWidth:true; variant:(root.controller && (root.controller.grounding.unsupported||0)>0)?"warning":"info"; text:"Factual News script sentences keep claim links. Manual factual edits must be reviewed before production." }
        RowLayout { Layout.fillWidth:true; AppButton { text:"Build from Approved Facts"; onClicked:root.controller.buildScript("") }; SecondaryButton { text:"Validate Grounding"; onClicked:root.controller.validateScript() }; SecondaryButton { text:"Open Script Editor"; onClicked:root.navigateRequested("script") } }
        RowLayout { Layout.fillWidth:true; SecondaryButton { text:"Translate"; onClicked:root.navigateRequested("translation") }; SecondaryButton { text:"Voice"; onClicked:root.navigateRequested("script") }; SecondaryButton { text:"Create Scenes"; onClicked:root.controller.createScenes() }; SecondaryButton { text:"AI Director"; onClicked:root.controller.createDirectorPlan(); } }
        Item { Layout.fillHeight:true }
    }
}
