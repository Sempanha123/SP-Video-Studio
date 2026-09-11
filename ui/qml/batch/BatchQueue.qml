import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { id:root; property var controller; signal itemSelected(var itemData)
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            ComboBox { id:filter; model:["all","running","pending","completed","failed","skipped"]; onActivated:controller.setQueueFilter(currentText,search.text) }
            TextField { id:search; Layout.fillWidth:true; placeholderText:"Search item, key or output"; onTextChanged:controller.setQueueFilter(filter.currentText,text) }
            Button { text:"Retry Failed"; onClicked:controller.retryAllFailed() }
        }
        ListView { Layout.fillWidth:true; Layout.fillHeight:true; clip:true; model:controller ? controller.items : []
            delegate:BatchItemRow { width:ListView.view.width; itemData:modelData; controller:root.controller; onSelected:root.itemSelected(data) }
        }
    }
}
