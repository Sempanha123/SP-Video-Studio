import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
AppCard {
    id: root
    property var controller
    property string claimId: ""
    property string sourceId: ""
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        SectionHeader { title: "Add News Graphic"; subtitle: "Graphics never invent facts. Claim-linked cards use approved News data." }
        AppComboBox { id: claim; Layout.fillWidth: true; model: root.controller ? root.controller.approvedClaims : []; textRole: "text"; valueRole: "id"; onActivated: root.claimId=String(currentValue||"") }
        RowLayout { Layout.fillWidth: true
            AppButton { text: "Fact"; compact: true; enabled: root.claimId!==""; onClicked: root.controller.createFact(root.claimId) }
            SecondaryButton { text: "Quote"; compact: true; enabled: root.claimId!==""; onClicked: root.controller.createQuote(root.claimId) }
        }
        AppComboBox { id: source; Layout.fillWidth: true; model: root.controller ? root.controller.sources : []; textRole: "title"; valueRole: "id"; onActivated: root.sourceId=String(currentValue||"") }
        SecondaryButton { text: "Source Attribution"; compact: true; enabled: root.sourceId!==""; onClicked: root.controller.createSource(root.sourceId) }
        AppTextField { id: headline; Layout.fillWidth: true; placeholderText: "Headline (manual/editor supplied)" }
        RowLayout { Layout.fillWidth: true
            SecondaryButton { text: "Headline"; compact: true; enabled: headline.text.trim().length>0; onClicked: root.controller.createHeadline(headline.text,"",root.sourceId,false) }
            SecondaryButton { text: "Breaking"; compact: true; enabled: headline.text.trim().length>0; onClicked: root.controller.createHeadline(headline.text,"",root.sourceId,true) }
            SecondaryButton { text: "Topic"; compact: true; enabled: headline.text.trim().length>0; onClicked: root.controller.createTopic(headline.text) }
        }
        RowLayout { Layout.fillWidth: true
            AppTextField { id: numberValue; Layout.preferredWidth: 90; placeholderText: "42" }
            AppTextField { id: numberUnit; Layout.preferredWidth: 90; placeholderText: "%" }
            AppTextField { id: numberLabel; Layout.fillWidth: true; placeholderText: "Confirmed label" }
            SecondaryButton { text: "Number"; compact: true; enabled: numberValue.text!=="" && numberLabel.text!==""; onClicked: root.controller.createNumber(numberValue.text,numberUnit.text,numberLabel.text,root.claimId,root.sourceId) }
        }
        RowLayout { Layout.fillWidth: true
            AppTextField { id: lowerPrimary; Layout.fillWidth: true; placeholderText: "Lower-third primary" }
            AppTextField { id: lowerSecondary; Layout.fillWidth: true; placeholderText: "Secondary" }
            SecondaryButton { text: "Lower Third"; compact: true; enabled: lowerPrimary.text!==""; onClicked: root.controller.createLowerThird(lowerPrimary.text,lowerSecondary.text,root.sourceId) }
        }
    }
}
