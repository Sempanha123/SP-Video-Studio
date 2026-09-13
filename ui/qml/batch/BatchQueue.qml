import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id: root; property var controller; signal itemSelected(var itemData)
    Timer { id: searchDebounce; interval: 220; repeat: false; onTriggered: if(controller) controller.setQueueFilter(filter.currentText, search.text) }
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.sm
            AppComboBox { id: filter; accessibleName:"Batch status filter"; Layout.preferredWidth: 136; model: ["all","running","pending","completed","failed","skipped"]; onActivated: { searchDebounce.stop(); controller.setQueueFilter(currentText, search.text) } }
            SearchField { id: search; Layout.fillWidth: true; placeholderText: "Search item, key or output"; onTextChanged: searchDebounce.restart(); onClearRequested: { searchDebounce.stop(); controller.setQueueFilter(filter.currentText,"") } }
            AppButton { text: "Retry Failed"; variant: "secondary"; size: "small"; onClicked: controller.retryAllFailed() }
        }
        Item { Layout.fillWidth:true; Layout.fillHeight:true
            ListView { id: queueView; anchors.fill:parent; Accessible.role:Accessible.List; Accessible.name:"Batch queue"; clip: true; spacing: 2; reuseItems: true; cacheBuffer: 420; model: controller ? controller.items : []
            property bool loadRequested: false
            onCountChanged: loadRequested=false
            onContentYChanged: if(controller && controller.hasMoreItems && !loadRequested && contentY+height>=contentHeight-160){loadRequested=true;controller.loadMoreItems()}
                delegate: BatchItemRow { width: ListView.view.width; itemData: modelData; controller: root.controller; onSelected: root.itemSelected(data) }
            }
            FriendlyEmptyState { anchors.centerIn:parent; visible:!root.controller || root.controller.items.length===0; title:"No Batch Items yet"; description:"Prepare the queue after validating your Batch inputs and mappings."; iconName:"batch" }
        }
    }
}
